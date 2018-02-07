import os
import numpy as np
import pandas as pd


class ScenarioMatrix(object):
    def __init__(self, region, year, combos, soil_data, crop_params, crop_dates, met_data, qc_file, output_format):

        # Set paths
        self.outfile = output_format.format(region, year)
        self.qc_table = pd.read_csv(qc_file).set_index('parameter')
        self.qc_outfile = self.outfile.rstrip(".csv") + "_qa.csv"

        # Use only unique combinations of weather grid, cdl, and soil id
        self.matrix = combos[['weather_grid', 'cdl', 'soil_id', 'scenario_id']].drop_duplicates()

        # Create duplicate scenarios for double-cropped classes
        self.add_double_crops()

        # Merge all tables
        self.matrix = self.matrix.merge(crop_params, left_on='cdl', right_on='gen_class', how='left')
        self.matrix = self.matrix.merge(crop_dates, on=('weather_grid', 'gen_class'), how='left')
        self.matrix = self.matrix.merge(soil_data, on="soil_id", how="left")
        self.matrix = self.matrix.merge(met_data, left_on='weather_grid', right_on='stationID', how='left')

        # Perform other scenario attribution tasks
        self.scenario_attribution()

        # Clean up matrix and write to file
        self.finalize()
        self.save()

    def scenario_attribution(self):

        # Process curve number
        from params import num_to_hsg
        num_to_hsg.update({2: "A", 4: "B", 6: "C"})  # A/D -> A, B/D -> B, C/D -> C
        for num, hsg in num_to_hsg.items():
            self.matrix.loc[self.matrix.hydro_group == num, 'cn_ag'] = self.matrix['cn_ag_' + hsg]
            self.matrix.loc[self.matrix.hydro_group == num, 'cn_fallow'] = self.matrix['cn_fallow_' + hsg]

        # /D soils are evenly numbered, selected with hsg % 2 = 0
        non_cultivated_slash_d = ((self.matrix.cultivated == 0) & (np.float32(self.matrix.hydro_group) % 2 == 0))
        self.matrix.loc[non_cultivated_slash_d, ['cn_ag', 'cn_fallow']] = \
            self.matrix[['cn_ag_D', 'cn_fallow_D']].loc[non_cultivated_slash_d]

        # Deal with maximum rooting depth
        self.matrix.loc[self.matrix.root_zone_max < self.matrix.amxdr, 'amxdr'] = self.matrix.root_zone_max

        # Assign snowmelt factor (sfac)
        self.matrix['sfac'] = 0.36
        self.matrix.loc[self.matrix.cdl.isin((60, 70, 140, 190)), 'sfac'] = .16

        # Assign missing crop dates
        empty = pd.isnull(self.matrix[['plant_begin', 'emergence_begin', 'maturity_begin', 'harvest_begin']])
        emergence = ~empty.plant_begin & empty.emergence_begin
        maturity = ~empty.plant_begin & ~empty.harvest_begin & empty.maturity_begin

        # Emergence 7 days after planting, maturity halfway between plant and harvest
        self.matrix.loc[emergence, 'emergence_begin'] = self.matrix.plant_begin[emergence] + 7
        self.matrix.loc[maturity, 'maturity_begin'] = \
            ((self.matrix.plant_begin + self.matrix.harvest_begin) / 2)[maturity]

    def add_double_crops(self):
        """ Join CDL-class-specific parameters to the table and add new rows for double cropped classes """
        from params import double_crops

        # Process double crops
        self.matrix['orig_cdl'] = self.matrix['cdl']
        self.matrix['overlay'] = 0  # Overlay crops aren't used to generate runoff in pesticide calculator
        all_new = []
        for old_crop, new_crops in double_crops.items():
            for i, new_crop in enumerate(new_crops):
                new_rows = self.matrix[self.matrix.orig_cdl == old_crop].copy()
                new_rows['cdl'] = new_crop
                new_rows['overlay'] = i
                all_new.append(new_rows)
        new_data = pd.concat(all_new, axis=0)
        self.matrix = pd.concat([self.matrix, new_data], axis=0)

    def finalize(self):
        """ Perform a quality check and fill missing data """
        from fields import scenario_matrix_fields

        # Trim
        self.matrix = self.matrix[scenario_matrix_fields].reset_index(drop=True)
        self.qc_table = self.qc_table.drop('cintcp')  # jch - temporary

        # Flag missing data
        flags = pd.isnull(self.matrix)[self.qc_table.index.values].mul(self.qc_table.blank_flag)

        # Flag out-of-range data
        for test in ('general', 'range'):
            ranges = self.qc_table[[test + "_min", test + "_max", test + "_flag"]].dropna().astype(np.int8)
            for param, (param_min, param_max, flag) in ranges.iterrows():
                out_of_range = (self.matrix[param] < param_min) | (self.matrix[param] > param_max)
                if out_of_range.any():
                    flags.loc[out_of_range, param] = np.maximum(flags.loc[out_of_range, param].as_matrix(), flag)

        # Write QC file
        flags.to_csv(self.qc_outfile)

        # Fill missing data
        self.matrix.fillna(self.qc_table.fill_value, inplace=True)

    def save(self):
        self.matrix.to_csv(os.path.join(self.outfile), index=False)


class Recipes(object):
    def __init__(self, region, year, combos, output_format):
        self.outfile = output_format.format(region, year)
        self.comids = combos.comid.as_matrix()
        self.recipes = combos[['scenario_id', 'area']]

        # Generate a map of which rows correspond to which comids
        self.recipe_map = self.map_recipes()

        # Save to file
        self.save()

    def map_recipes(self):
        first_rows = np.hstack(([0], np.where(self.comids[:-1] != self.comids[1:])[0] + 1))
        last_rows = np.hstack((first_rows[1:], [self.comids.size]))
        return np.vstack((self.comids[first_rows], first_rows, last_rows)).T

    def save(self):
        if not os.path.exists(os.path.dirname(self.outfile)):
            os.makedirs(os.path.dirname(self.outfile))
        np.savez_compressed(self.outfile, data=self.recipes.as_matrix(), map=self.recipe_map)


def read_tables(crop_params_path, crop_dates_path, metfile_path):
    from fields import kurt_fields, crop_event_fields, crop_params_fields

    # Read and modify crop dates
    crop_dates_fields = crop_event_fields + kurt_fields
    crop_dates = pd.read_csv(crop_dates_path).rename(columns=crop_dates_fields.convert)
    for missing_field in set(crop_dates_fields.new) - set(crop_dates.columns.values):
        crop_dates[missing_field] = -1
    crop_dates = crop_dates[crop_dates_fields.new]
    crop_dates[['weather_grid', 'gen_class']] = crop_dates[['weather_grid', "gen_class"]].astype(np.int32)

    # Read crop params
    crop_params = pd.read_csv(crop_params_path).rename(columns=crop_params_fields.convert)
    del crop_params['cdl']

    # Read table with weather grid parameters
    met_data = pd.read_csv(metfile_path)

    return crop_params, crop_dates, met_data


def read_combinations(region, year, soil_path, combo_path, aggregate):
    matrix = pd.DataFrame(dtype=np.int32, **np.load(os.path.join(combo_path, "{}_{}.npz".format(region, year))))
    if aggregate:
        aggregation_key = pd.read_csv(os.path.join(soil_path, "{}_aggregation_map.txt".format(region)))
        matrix = matrix.merge(aggregation_key, on='mukey', how='left')
        matrix = matrix.rename(columns={'aggregation_key': 'soil_id'})
        del matrix['mukey']
        matrix = matrix.groupby(['comid', 'weather_grid', 'cdl', 'soil_id']).sum().reset_index()
    else:
        matrix = matrix.rename(columns={'mukey': 'soil_id'})
        del matrix['aggregation_key']

    # Create a CDL/weather/soil identifier to link Recipes and Scenarios
    matrix['scenario_id'] = matrix.soil_id.astype("str") + 'w' + \
                            matrix.weather_grid.astype("str") + 'lc' + \
                            matrix.cdl.astype("str")
    return matrix


def read_soils(region, soil_path, aggregate):
    soil_file_format = '{}_aggregated_soil.txt' if aggregate else '{}_unaggregated_soil.txt'
    soil_fields = {"aggregation_key": "soil_id", "mukey": "soil_id"}
    soil_path = os.path.join(soil_path, soil_file_format.format(region))
    return pd.read_csv(soil_path).rename(columns=soil_fields)


def main():
    from utilities import nhd_states

    # Specify paths here
    combo_path = os.path.join("..", "bin", "Preprocessed", "Combos")
    soil_path = os.path.join("..", "bin", "Preprocessed", "Soils")
    crop_params_path = os.path.join("..", "bin", "Tables", "cdl_params.csv")
    crop_dates_path = os.path.join("..", "bin", "Tables", "crop_dates_122017.csv")
    metfile_path = os.path.join("..", "bin", "Tables", "met_data.csv")
    recipe_output_path = os.path.join("..", "bin", "Preprocessed", "RecipeFiles", "r{}_{}.npz")
    scenario_output_path = os.path.join("..", "bin", "Preprocessed", "ScenarioMatrices", "r{}_{}.csv")
    scenario_qc_table = os.path.join("..", "bin", "Tables", "scenario_matrix_qc.csv")

    # Specify run parameters here
    regions = ['07']  # all regions: sorted(nhd_states.keys())
    years = ['2010']
    generate_recipes = False
    aggregate = True

    print("Reading tables...")
    crop_params, crop_dates, met_data = read_tables(crop_params_path, crop_dates_path, metfile_path)

    for region in regions:

        print("Reading soil data...")
        soil_data = read_soils(region, soil_path, aggregate)

        for year in years:
            print("Reading combos...")
            # combos = read_combinations(region, year, soil_path, combo_path, aggregate)
            # combos.to_csv('intermediate.csv')
            combos = pd.read_csv('intermediate.csv', index_col=0)
            if generate_recipes:
                print("Generating recipes...")
                Recipes(region, year, combos, recipe_output_path)

            print("Generating scenarios...")
            ScenarioMatrix(region, year, combos, soil_data, crop_params, crop_dates, met_data, scenario_qc_table,
                           scenario_output_path)


main()
