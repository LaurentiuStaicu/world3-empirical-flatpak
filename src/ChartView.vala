public class World3Empirical.ChartView : Gtk.DrawingArea {
    private ScenarioData? data;
    private int start_year = 1960;
    private int end_year = 2050;
    private bool show_uncertainty = true;
    private bool hover_active = false;
    private double hover_x = 0;
    private double hover_y = 0;
    private string unit_label = "";
    private int projection_cutoff = 2025;
    private bool has_observations = true;

    private const double LEFT = 68;
    private const double RIGHT = 26;
    private const double TOP = 72;
    private const double BOTTOM = 48;

    public ChartView () {
        set_content_width (760);
        set_content_height (440);
        set_hexpand (true);
        set_vexpand (true);
        set_draw_func (draw_chart);
        add_css_class ("card");
        tooltip_text = "Deplasează pointerul pentru anul și valorile celor trei modele";

        var motion = new Gtk.EventControllerMotion ();
        motion.motion.connect ((x, y) => {
            hover_x = x;
            hover_y = y;
            hover_active = true;
            queue_draw ();
        });
        motion.leave.connect (() => {
            hover_active = false;
            queue_draw ();
        });
        add_controller (motion);
    }

    public void set_series (ScenarioData selected, string unit, int cutoff, bool observed) {
        data = selected;
        unit_label = unit;
        projection_cutoff = cutoff;
        has_observations = observed;
        queue_draw ();
    }

    public void set_year_range (int first, int last) {
        start_year = first;
        end_year = last;
        queue_draw ();
    }

    public void set_show_uncertainty (bool enabled) {
        show_uncertainty = enabled;
        queue_draw ();
    }

    private bool valid (double value) {
        return value.is_finite ();
    }

    private void draw_chart (Gtk.DrawingArea area, Cairo.Context context, int width, int height) {
        if (data == null || width < 300 || height < 220) {
            return;
        }

        double chart_width = width - LEFT - RIGHT;
        double chart_height = height - TOP - BOTTOM;
        double minimum = double.MAX;
        double maximum = -double.MAX;
        int[] scaling_series = {
            ScenarioData.OBSERVED,
            ScenarioData.ORIGINAL_BAU,
            ScenarioData.ORIGINAL_BAU2,
            ScenarioData.HYBRID_2026
        };

        for (int index = 0; index < data.length; index++) {
            double year = data.year_at_index (index);
            if (year < start_year || year > end_year) {
                continue;
            }
            foreach (int series in scaling_series) {
                include_value (data.value_at_index (series, index), ref minimum, ref maximum);
            }
            if (show_uncertainty) {
                include_value (data.value_at_index (ScenarioData.P10, index), ref minimum, ref maximum);
                include_value (data.value_at_index (ScenarioData.P90, index), ref minimum, ref maximum);
            }
        }
        if (minimum == double.MAX || maximum == -double.MAX) {
            return;
        }
        double span = maximum - minimum;
        if (span <= 0) {
            span = 1;
        }
        minimum -= span * 0.07;
        if (minimum < 0) {
            minimum = 0;
        }
        maximum += span * 0.09;
        double tick_step = 1;
        nice_axis (ref minimum, ref maximum, out tick_step);

        draw_horizontal_grid (context, chart_width, chart_height, minimum, maximum, tick_step);
        draw_year_grid (context, chart_width, chart_height);

        if (show_uncertainty) {
            draw_band (context, LEFT, TOP, chart_width, chart_height, minimum, maximum);
        }
        draw_line (context, ScenarioData.ORIGINAL_BAU, LEFT, TOP, chart_width, chart_height,
                   minimum, maximum, rgba ("#7f8c8d", 0.95), 1.8, true);
        draw_line (context, ScenarioData.ORIGINAL_BAU2, LEFT, TOP, chart_width, chart_height,
                   minimum, maximum, rgba ("#e67e22", 0.95), 2.0, true);
        int cutoff = projection_cutoff;
        draw_line_range (context, ScenarioData.HYBRID_2026, LEFT, TOP, chart_width, chart_height,
                         minimum, maximum, rgba ("#3689e6", 0.62), 2.0, true,
                         start_year, cutoff);
        draw_line_range (context, ScenarioData.HYBRID_2026, LEFT, TOP, chart_width, chart_height,
                         minimum, maximum, rgba ("#3689e6", 1), 3.0, false,
                         cutoff, end_year);
        if (has_observations) {
            draw_points (context, LEFT, TOP, chart_width, chart_height, minimum, maximum);
        }
        draw_cutoff (context, chart_width, chart_height);
        draw_legend (context, LEFT + 8, 18);
        draw_unit_label (context);

        if (hover_active
            && hover_x >= LEFT && hover_x <= LEFT + chart_width
            && hover_y >= TOP && hover_y <= TOP + chart_height) {
            draw_hover (context, width, chart_width, chart_height, minimum, maximum);
        }
    }

    private void include_value (double value, ref double minimum, ref double maximum) {
        if (!valid (value)) {
            return;
        }
        if (value < minimum) { minimum = value; }
        if (value > maximum) { maximum = value; }
    }

    private void nice_axis (ref double minimum, ref double maximum, out double step) {
        double raw_step = (maximum - minimum) / 6.0;
        double exponent = Math.floor (Math.log10 (raw_step));
        double power = Math.pow (10.0, exponent);
        double fraction = raw_step / power;
        double nice_fraction;
        if (fraction <= 1.0) { nice_fraction = 1.0; }
        else if (fraction <= 2.0) { nice_fraction = 2.0; }
        else if (fraction <= 2.5) { nice_fraction = 2.5; }
        else if (fraction <= 5.0) { nice_fraction = 5.0; }
        else { nice_fraction = 10.0; }
        step = nice_fraction * power;
        minimum = Math.floor (minimum / step) * step;
        maximum = Math.ceil (maximum / step) * step;
        if (minimum < 0) { minimum = 0; }
    }

    private void draw_horizontal_grid (Cairo.Context context, double chart_width,
                                       double chart_height, double minimum, double maximum,
                                       double step) {
        context.select_font_face ("Sans", Cairo.FontSlant.NORMAL, Cairo.FontWeight.NORMAL);
        context.set_font_size (11);
        int intervals = (int) Math.round ((maximum - minimum) / step);
        for (int line = 0; line <= intervals; line++) {
            double value = maximum - step * line;
            double y = y_for (value, TOP, chart_height, minimum, maximum);
            set_color (context, rgba ("#7f8c8d", 0.24));
            context.set_line_width (1);
            context.move_to (LEFT, y);
            context.line_to (LEFT + chart_width, y);
            context.stroke ();
            set_color (context, rgba ("#65737e", 0.95));
            context.move_to (8, y + 4);
            context.show_text (format_axis_value (value, step));
        }
    }

    private void draw_unit_label (Cairo.Context context) {
        context.select_font_face ("Sans", Cairo.FontSlant.NORMAL, Cairo.FontWeight.NORMAL);
        context.set_font_size (10);
        set_color (context, rgba ("#65737e", 0.95));
        context.move_to (LEFT + 8, 52);
        context.show_text ("Unitate: " + unit_label);
    }

    private void draw_year_grid (Cairo.Context context, double chart_width, double chart_height) {
        int first_mark = ((start_year + 4) / 5) * 5;
        context.set_font_size (10);
        for (int year = first_mark; year <= end_year; year += 5) {
            bool major = year % 10 == 0;
            double x = x_for (year, LEFT, chart_width);
            set_color (context, rgba ("#7f8c8d", major ? 0.25 : 0.10));
            context.set_line_width (major ? 1.0 : 0.7);
            context.move_to (x, TOP);
            context.line_to (x, TOP + chart_height);
            context.stroke ();
            bool label_year = (end_year - start_year <= 100) || major;
            if (label_year) {
                set_color (context, rgba ("#65737e", 0.95));
                context.move_to (x - 13, TOP + chart_height + 25);
                context.show_text (year.to_string ());
            }
        }
    }

    private void draw_band (Cairo.Context context, double left, double top,
                            double width, double height, double minimum, double maximum) {
        bool started = false;
        for (int index = 0; index < data.length; index++) {
            double year = data.year_at_index (index);
            double value = data.value_at_index (ScenarioData.P90, index);
            if (year < start_year || year > end_year || !valid (value)) { continue; }
            double x = x_for (year, left, width);
            double y = y_for (value, top, height, minimum, maximum);
            if (!started) { context.move_to (x, y); started = true; }
            else { context.line_to (x, y); }
        }
        if (!started) { return; }
        for (int index = data.length - 1; index >= 0; index--) {
            double year = data.year_at_index (index);
            double value = data.value_at_index (ScenarioData.P10, index);
            if (year < start_year || year > end_year || !valid (value)) { continue; }
            context.line_to (x_for (year, left, width), y_for (value, top, height, minimum, maximum));
        }
        context.close_path ();
        set_color (context, rgba ("#3689e6", 0.14));
        context.fill ();
    }

    private void draw_line (Cairo.Context context, int series, double left, double top,
                            double width, double height, double minimum, double maximum,
                            Gdk.RGBA color, double line_width, bool dashed) {
        draw_line_range (context, series, left, top, width, height, minimum, maximum,
                         color, line_width, dashed, start_year, end_year);
    }

    private void draw_line_range (Cairo.Context context, int series, double left, double top,
                                  double width, double height, double minimum, double maximum,
                                  Gdk.RGBA color, double line_width, bool dashed,
                                  int first_year, int last_year) {
        bool drawing = false;
        set_color (context, color);
        context.set_line_width (line_width);
        context.set_dash (dashed ? new double[] { 7, 5 } : new double[] {}, 0);
        for (int index = 0; index < data.length; index++) {
            double year = data.year_at_index (index);
            double value = data.value_at_index (series, index);
            if (year < start_year || year > end_year
                || year < first_year || year > last_year || !valid (value)) {
                if (drawing) { context.stroke (); drawing = false; }
                continue;
            }
            double x = x_for (year, left, width);
            double y = y_for (value, top, height, minimum, maximum);
            if (!drawing) { context.move_to (x, y); drawing = true; }
            else { context.line_to (x, y); }
        }
        if (drawing) { context.stroke (); }
        context.set_dash ({}, 0);
    }

    private void draw_points (Cairo.Context context, double left, double top,
                              double width, double height, double minimum, double maximum) {
        set_color (context, rgba ("#17202a", 1));
        for (int index = 0; index < data.length; index++) {
            double year = data.year_at_index (index);
            double value = data.value_at_index (ScenarioData.OBSERVED, index);
            if (year < start_year || year > end_year || !valid (value)) { continue; }
            context.arc (x_for (year, left, width), y_for (value, top, height, minimum, maximum),
                         2.5, 0, 2 * Math.PI);
            context.fill ();
        }
    }

    private void draw_cutoff (Cairo.Context context, double chart_width, double chart_height) {
        int cutoff = projection_cutoff;
        if (cutoff < start_year || cutoff > end_year) { return; }
        double x = x_for (cutoff, LEFT, chart_width);
        set_color (context, rgba ("#c0392b", 0.70));
        context.set_dash ({ 4, 4 }, 0);
        context.set_line_width (1.1);
        context.move_to (x, TOP);
        context.line_to (x, TOP + chart_height);
        context.stroke ();
        context.set_dash ({}, 0);
        context.set_font_size (10);
        set_color (context, rgba ("#c0392b", 0.95));
        context.move_to (x + 5, TOP + 12);
        context.show_text (has_observations
            ? "observații până în %d".printf (cutoff)
            : "proiecție după %d".printf (cutoff));
    }

    private void draw_legend (Cairo.Context context, double x, double y) {
        context.set_font_size (10.5);
        double offset = 0;
        if (has_observations) {
            draw_point_legend (context, x, y, "date observate");
            offset = 122;
        }
        legend_item (context, x + offset, y, rgba ("#7f8c8d", 0.95), "BAU original", true);
        legend_item (context, x + offset + 122, y, rgba ("#e67e22", 0.95), "BAU2 original", true);
        hybrid_legend_item (context, x + offset + 252, y, "BAU Hibrid 2026");
        if (show_uncertainty) {
            set_color (context, rgba ("#3689e6", 0.14));
            context.rectangle (x + offset + 406, y - 8, 18, 10);
            context.fill ();
            set_color (context, rgba ("#3d4852", 1));
            context.move_to (x + offset + 429, y);
            context.show_text ("P10–P90 structural");
        }
    }

    private void hybrid_legend_item (Cairo.Context context, double x, double y, string label) {
        set_color (context, rgba ("#3689e6", 0.62));
        context.set_dash ({ 3, 3 }, 0);
        context.set_line_width (2);
        context.move_to (x, y - 4);
        context.line_to (x + 8, y - 4);
        context.stroke ();
        context.set_dash ({}, 0);
        set_color (context, rgba ("#3689e6", 1));
        context.set_line_width (3);
        context.move_to (x + 10, y - 4);
        context.line_to (x + 20, y - 4);
        context.stroke ();
        set_color (context, rgba ("#3d4852", 1));
        context.move_to (x + 25, y);
        context.show_text (label);
    }

    private void draw_point_legend (Cairo.Context context, double x, double y, string label) {
        set_color (context, rgba ("#17202a", 1));
        context.arc (x + 9, y - 4, 2.7, 0, 2 * Math.PI);
        context.fill ();
        set_color (context, rgba ("#3d4852", 1));
        context.move_to (x + 18, y);
        context.show_text (label);
    }

    private void legend_item (Cairo.Context context, double x, double y,
                              Gdk.RGBA color, string label, bool dashed) {
        set_color (context, color);
        context.set_dash (dashed ? new double[] { 5, 3 } : new double[] {}, 0);
        context.set_line_width (2);
        context.move_to (x, y - 4);
        context.line_to (x + 18, y - 4);
        context.stroke ();
        context.set_dash ({}, 0);
        set_color (context, rgba ("#3d4852", 1));
        context.move_to (x + 23, y);
        context.show_text (label);
    }

    private void draw_hover (Cairo.Context context, int total_width, double chart_width,
                             double chart_height, double minimum, double maximum) {
        int year = (int) Math.round (
            start_year + (hover_x - LEFT) * (end_year - start_year) / chart_width
        );
        if (year < start_year) { year = start_year; }
        if (year > end_year) { year = end_year; }
        double x = x_for (year, LEFT, chart_width);

        set_color (context, rgba ("#34495e", 0.55));
        context.set_line_width (1);
        context.set_dash ({ 3, 3 }, 0);
        context.move_to (x, TOP);
        context.line_to (x, TOP + chart_height);
        context.stroke ();
        context.set_dash ({}, 0);

        double panel_width = 330;
        double panel_height = show_uncertainty ? 154 : 135;
        double panel_x = x + 14;
        if (panel_x + panel_width > total_width - 8) {
            panel_x = x - panel_width - 14;
        }
        double panel_y = TOP + 12;
        set_color (context, rgba ("#ffffff", 0.96));
        context.rectangle (panel_x, panel_y, panel_width, panel_height);
        context.fill_preserve ();
        set_color (context, rgba ("#566573", 0.75));
        context.set_line_width (1);
        context.stroke ();

        context.select_font_face ("Sans", Cairo.FontSlant.NORMAL, Cairo.FontWeight.BOLD);
        context.set_font_size (12);
        set_color (context, rgba ("#17202a", 1));
        context.move_to (panel_x + 11, panel_y + 18);
        string phase = year <= projection_cutoff ? "retrospectiv" : "proiecție";
        context.show_text ("Anul %d · %s".printf (year, phase));
        context.select_font_face ("Sans", Cairo.FontSlant.NORMAL, Cairo.FontWeight.NORMAL);
        context.set_font_size (9.5);
        set_color (context, rgba ("#65737e", 1));
        context.move_to (panel_x + 11, panel_y + 35);
        context.show_text ("Unitate: " + unit_label);
        context.set_font_size (10.5);

        double line_y = panel_y + 56;
        if (has_observations) {
            hover_line (context, panel_x + 11, line_y, rgba ("#17202a", 1),
                        "Observat", data.value_at (ScenarioData.OBSERVED, year));
            line_y += 19;
        }
        hover_line (context, panel_x + 11, line_y, rgba ("#7f8c8d", 1),
                    "BAU original", data.value_at (ScenarioData.ORIGINAL_BAU, year));
        line_y += 19;
        hover_line (context, panel_x + 11, line_y, rgba ("#e67e22", 1),
                    "BAU2 original", data.value_at (ScenarioData.ORIGINAL_BAU2, year));
        line_y += 19;
        hover_line (context, panel_x + 11, line_y, rgba ("#3689e6", 1),
                    "BAU Hibrid 2026", data.value_at (ScenarioData.HYBRID_2026, year));
        if (show_uncertainty) {
            line_y += 19;
            double low = data.value_at (ScenarioData.P10, year);
            double high = data.value_at (ScenarioData.P90, year);
            string interval = valid (low) && valid (high)
                ? "%s – %s".printf (format_value (low), format_value (high))
                : "—";
            set_color (context, rgba ("#3689e6", 0.75));
            context.rectangle (panel_x + 11, line_y - 8, 12, 7);
            context.fill ();
            set_color (context, rgba ("#34495e", 1));
            context.move_to (panel_x + 29, line_y);
            context.show_text ("P10–P90: " + interval);
        }
    }

    private void hover_line (Cairo.Context context, double x, double y, Gdk.RGBA color,
                             string label, double value) {
        set_color (context, color);
        context.set_line_width (2.4);
        context.move_to (x, y - 4);
        context.line_to (x + 12, y - 4);
        context.stroke ();
        set_color (context, rgba ("#34495e", 1));
        context.move_to (x + 18, y);
        string rendered = valid (value) ? format_value (value) : "—";
        context.show_text ("%s: %s".printf (label, rendered));
    }

    private double x_for (double year, double left, double width) {
        return left + width * (year - start_year) / (end_year - start_year);
    }

    private double y_for (double value, double top, double height,
                          double minimum, double maximum) {
        return top + height * (maximum - value) / (maximum - minimum);
    }

    private Gdk.RGBA rgba (string hex, double alpha) {
        var color = Gdk.RGBA ();
        color.parse (hex);
        color.alpha = (float) alpha;
        return color;
    }

    private void set_color (Cairo.Context context, Gdk.RGBA color) {
        context.set_source_rgba (color.red, color.green, color.blue, color.alpha);
    }

    private string format_value (double value) {
        if (value >= 1000) { return "%.0f".printf (value); }
        if (value >= 100) { return "%.1f".printf (value); }
        if (value >= 10) { return "%.2f".printf (value); }
        if (value >= 1) { return "%.3f".printf (value); }
        return "%.4f".printf (value);
    }

    private string format_axis_value (double value, double step) {
        if (step >= 1) { return "%.0f".printf (value); }
        if (step >= 0.1) { return "%.1f".printf (value); }
        if (step >= 0.01) { return "%.2f".printf (value); }
        return "%.3f".printf (value);
    }
}
