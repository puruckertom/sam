import numpy as np

import read
import pesticide_applications as applications
import pesticide_functions as functions
import output


def main_calculator(input_file, recipe_dir, scenario_dir, hydro_dir, output_dir, flow_file, recipe_format, hydro_format,
                    output_format, input_years):

    # Read in hardwired parameters (set in read.py)
    delta_x, foliar_deg, washoff, soil_2cm, runoff_effic = read.pesticide_parameters()

    # Read SAM input file
    start_count, dates, ndates, cropdesired, koc, kflag, appflag, distribflag, cropstage, stagedays, stageflag, \
    app_windows, appnumrec, appmass, appmethod_init, degradation_aqueous = read.input_file(input_file)

    # Find and assemble recipes
    recipe_files = read.recipes(recipe_dir, recipe_format, input_years, scenario_dir, cropdesired)

    # Loop through recipes and corresponding flows listed in flow file
    for recipe_id, q, _, xc in read.flows(flow_file, dates):

        print(recipe_id)

        total_runoff_by_year = read.hydro(hydro_dir, hydro_format, recipe_id, input_years, start_count)

        for year in input_years:  # recipe_files[recipe_id]:

            scenarios = recipe_files[recipe_id][year]

            total_runoff = total_runoff_by_year[2010]  # @@@ - total_runoff_by_year[year] (not using 2011-2013)

            total_runoff_mass = np.zeros_like(total_runoff)  # Initializes an array to hold daily total runoff mass

            for scenario_file, area in scenarios:

                # Read scenario
                runoff, leaching, rain, plant_factor, soil_water, covmax, org_carbon, bulk_density = \
                    read.scenario(scenario_file, start_count)

                # Get the dates and amounts of pesticide applications
                pesticide_apps = \
                    applications.details(plant_factor, stageflag, distribflag, appnumrec, appmass, appmethod_init,
                                         app_windows, stagedays, cropstage)

                # Get the mass of pesticide in the soil at each time step
                pesticide_mass_soil = \
                    applications.process(pesticide_apps, plant_factor, rain, soil_2cm, covmax, foliar_deg, washoff)

                # Determine the loading of pesticide into runoff
                runoff_mass = functions.transport(koc, org_carbon, bulk_density, degradation_aqueous, soil_water, delta_x,
                                                  kflag, runoff, leaching, runoff_effic, pesticide_mass_soil)

                # Update total runoff
                total_runoff_mass += runoff_mass * area

            # Compute concentration in water
            q_tot, baseflow, total_conc, runoff_conc = \
                functions.waterbody_concentration(q, xc, total_runoff, total_runoff_mass)

            # Write daily output
            output.daily(output_dir, output_format,
                         recipe_id, total_conc, runoff_conc, total_runoff_mass, dates, q_tot, baseflow,
                         total_runoff, year)


def main():

    input_file = r"T:\SAM\FortranToPy\Inputs\SAM.inp"
    flow_file = r"T:\SAM\FortranToPy\MarkTwain\MO_flows.csv"

    recipe_dir = r"T:\SAM\FortranToPy\MarkTwain\Recipes"
    scenario_dir = r"T:\SAM\FortranToPy\MarkTwain\Scenarios\Pickled"
    hydro_dir = r"T:\SAM\FortranToPy\MarkTwain\Hydro"
    output_dir = r"T:\SAM\Outputs\Python"

    recipe_format = "nhd_recipe_(\d+?)_(\d{4}).txt"
    hydro_format = "{}_hydro.txt"
    output_format = "Eco_{}_{}_daily.out"

    input_years = [2010, 2011, 2012, 2013]

    main_calculator(input_file, recipe_dir, scenario_dir, hydro_dir, output_dir, flow_file, recipe_format,
                    hydro_format, output_format, input_years)

if __name__ == "__main__":
    #main()
    import cProfile
    cProfile.run("main()")