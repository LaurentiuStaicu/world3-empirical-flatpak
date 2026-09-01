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
        if (lines.length < 2) {
            throw new IOError.INVALID_DATA ("Fișier CSV gol sau fără antet: " + path);
        }

        var headers = lines[0].strip ().split (",");
        int year_column = require_column (headers, "year", path);
        int observed_column = require_column (headers, "observed", path);
        int bau_column = require_column (headers, "original_bau", path);
        int bau2_column = require_column (headers, "original_bau2", path);
        int hybrid_column = require_column (headers, "hybrid_2026", path);
        int p10_column = require_column (headers, "p10", path);
        int p90_column = require_column (headers, "p90", path);
        int benchmark_column = require_column (headers, "benchmark", path);
        int largest_column = year_column;
        int[] required_indices = {
            observed_column, bau_column, bau2_column, hybrid_column,
            p10_column, p90_column, benchmark_column
        };
        foreach (int index in required_indices) {
            if (index > largest_column) {
                largest_column = index;
            }
        }

        double previous_year = -double.MAX;
        for (int row = 1; row < lines.length; row++) {
            var line = lines[row].strip ();
            if (line == "") {
                continue;
            }
            var fields = line.split (",");
            if (fields.length <= largest_column) {
                throw new IOError.INVALID_DATA (
                    "%s: rândul %d are mai puține coloane decât antetul".printf (path, row + 1)
                );
            }
            double year = parse_value (fields[year_column]);
            if (!year.is_finite () || year <= previous_year) {
                throw new IOError.INVALID_DATA (
                    "%s: an lipsă, duplicat sau nesortat la rândul %d".printf (path, row + 1)
                );
            }
            previous_year = year;
            years_data += year;
            observed_data += parse_value (fields[observed_column]);
            original_bau_data += parse_value (fields[bau_column]);
            original_bau2_data += parse_value (fields[bau2_column]);
            hybrid_data += parse_value (fields[hybrid_column]);
            p10_data += parse_value (fields[p10_column]);
            p90_data += parse_value (fields[p90_column]);
            benchmark_data += parse_value (fields[benchmark_column]);
        }

        if (years_data.length == 0) {
            throw new IOError.INVALID_DATA ("Fișierul nu conține datele BAU Hibrid 2026");
        }
    }

    private double parse_value (string field) {
        var clean = field.strip ();
        return clean == "" ? double.NAN : double.parse (clean);
    }

    public static int require_column (string[] headers, string column, string path) throws Error {
        int result = -1;
        for (int index = 0; index < headers.length; index++) {
            if (headers[index].strip () == column) {
                if (result >= 0) {
                    throw new IOError.INVALID_DATA (path + ": coloană duplicată: " + column);
                }
                result = index;
            }
        }
        if (result < 0) {
            throw new IOError.INVALID_DATA (path + ": lipsește coloana obligatorie: " + column);
        }
        return result;
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
