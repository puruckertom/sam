import os
import shutil

recipe_ids = [18450435, 18450443, 18450445, 18450447, 18450455, 18449945, 18449947, 18449949, 18450461, 18449951,
              18449953, 18450465, 18449955, 18450467, 18449957, 18450979, 18449959, 18450469, 18450981, 18450985,
              18450987, 18449965, 18449967, 18449969, 18449975, 18450999, 18450489, 18451003, 18451005, 18450493,
              18449983, 18450495, 18451007, 18450497, 18451009, 18450499, 18451011, 18451013, 18450503, 18451015,
              18451017, 18450505, 18451019, 18451021, 18449997, 18451023, 18450511, 18449999, 18451025, 18451027,
              18450515, 18451029, 18450005, 18451031, 18451033, 18450521, 18450523, 18451035, 18451037, 18450013,
              18451039, 18450015, 18451041, 18450019, 18454629, 18450021, 18454631, 18450023, 18454633, 18450025,
              18454635, 18454637, 18451053, 18454639, 18450541, 18450551, 18450553, 18450043, 18451067, 18450045,
              18454653, 18450047, 18450555, 18450049, 18450559, 18450561, 18450563, 18450565, 18450567, 18450057,
              18450569, 18450059, 18450571, 18450573, 18454675, 18450579, 18450069, 18454677, 18454679, 18450585,
              18450587, 18450589, 18450591, 18450595, 18450597, 18451109, 18450603, 18450605, 18450607, 18451119,
              18451121, 18450609, 18450611, 18451123, 18450613, 18451125, 18451127, 18450615, 18450617, 18450619,
              18450621, 18459840, 18459842, 18454723, 18450627, 18454725, 18450629, 18454727, 18450631, 18454729,
              18454731, 18459854, 18450641, 18450643, 18459862, 18450651, 18450653, 18459870, 18450655, 18450663,
              18450665, 18450667, 18450669, 18450675, 18450677, 18450679, 18450681, 18450683, 18450689, 18450693,
              18450695, 18450697, 18450699, 18450703, 25168665, 18450719, 18450721, 25168673, 25168677, 18450725,
              25168681, 18450733, 25168685, 25168687, 18450737, 18450741, 18450745, 18450747, 18450749, 18450751,
              18450753, 18450767, 18450769, 18450771, 18450773, 18454427, 18454429, 18454431, 18454433, 18454443,
              18454445, 18450349, 18454447, 18454449, 18450353, 18454455, 18454457, 18454461, 18450877, 18454463,
              18454469, 18450373, 18450375, 18454473, 18454475, 18450379, 18454479, 18450383, 18450385, 18450387,
              18450391, 18450405, 18450407, 18450409, 18454511, 18450415, 18450419, 18450425]

old_dir = r"F:\EcoRecipes_nhd\indivMU\IN_individual_mapunits_recipes"
new_dir = r"S:\bin\Preprocessed\Recipes\WRB"

for year in range(2010, 2015):
    for recipe_id in recipe_ids:
        print(recipe_id, year)
        f = "nhd_recipe_{}_{}.txt".format(recipe_id, year)
        old_file = os.path.join(old_dir, f)
        new_file = os.path.join(new_dir, f)
        try:
            shutil.copy(old_file, new_file)
        except:
            print("FAIL")