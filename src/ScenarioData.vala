public class World3Empirical.ScenarioData : Object {
    public string name { get; construct; }
    public int length { get { return years_data.length; } }

    public const int OBSERVED = 0;
    public const int ORIGINAL_BAU = 1;
    public const int ORIGINAL_BAU2 = 2;
    public const int HYBRID_2026 = 3;
    public const int P10 = 4;
    public const int P90 = 5;
    public const int BENCHMARK = 6;

    private double[] years_data = {};
    private double[] observed_data = {};
    private double[] original_bau_data = {};
    private double[] original_bau2_data = {};
    private double[] hybrid_data = {};
    private double[] p10_data = {};
    private double[] p90_data = {};
    private double[] benchmark_data = {};

    public ScenarioData (string name, string path) throws Error {
        Object (name: name);
        string contents;
        FileUtils.get_contents (path, out contents);
        var lines = contents.split ("\n");
        for (int row = 1; row < lines.length; row++) {
            var line = lines[row].strip ();
            if (line == "") {
                continue;
            }
            var fields = line.split (",");
            if (fields.length < 13) {
                continue;
            }
            years_data += parse_value (fields[0]);
            observed_data += parse_value (fields[1]);
            original_bau2_data += parse_value (fields[2]);
            original_bau_data += parse_value (fields[4]);
            p10_data += parse_value (fields[6]);
            p90_data += parse_value (fields[7]);
            benchmark_data += parse_value (fields[11]);
            hybrid_data += parse_value (fields[12]);
        }

        if (years_data.length == 0) {
            throw new IOError.INVALID_DATA ("Fișierul nu conține datele BAU Hibrid 2026");
        }
    }

    private double parse_value (string field) {
        var clean = field.strip ();
        return clean == "" ? double.NAN : double.parse (clean);
    }

    public int last_observed_year () {
        int result = 0;
        for (int index = 0; index < length; index++) {
            if (observed_data[index].is_finite ()) {
                result = (int) years_data[index];
            }
        }
        return result;
    }

    public double value_at (int series, int year) {
        for (int index = 0; index < length; index++) {
            if ((int) years_data[index] == year) {
                return value_at_index (series, index);
            }
        }
        return double.NAN;
    }

    public double year_at_index (int index) {
        return years_data[index];
    }

    public double value_at_index (int series, int index) {
        switch (series) {
            case OBSERVED:
                return observed_data[index];
            case ORIGINAL_BAU:
                return original_bau_data[index];
            case ORIGINAL_BAU2:
                return original_bau2_data[index];
            case HYBRID_2026:
                return hybrid_data[index];
            case P10:
                return p10_data[index];
            case P90:
                return p90_data[index];
            case BENCHMARK:
                return benchmark_data[index];
            default:
                return double.NAN;
        }
    }

    public bool has_values (int series) {
        for (int index = 0; index < length; index++) {
            if (value_at_index (series, index).is_finite ()) {
                return true;
            }
        }
        return false;
    }
}
