public class World3Empirical.MainWindow : Gtk.ApplicationWindow {
    private const string DATA_DIRECTORY = "/app/share/io.github.laurentiustaicu.World3Empirical/scenarios";
    private const int CALIBRATED_INDICATOR_COUNT = 5;
    private const string[] KEYS = {
        "population",
        "industry_per_capita",
        "food_per_capita",
        "pollution_pressure",
        "human_welfare",
        "industry_total",
        "persistent_pollution_stock",
        "resources_remaining_pct"
    };
    private const string[] LABELS = {
        "Populație mondială",
        "Producție industrială pe locuitor",
        "Producție alimentară pe locuitor",
        "Emisii CO₂ anuale (proxy activitate)",
        "Dezvoltare umană",
        "Producție industrială totală",
        "Stoc de poluare persistentă (latent)",
        "Resurse neregenerabile rămase (latent)"
    };
    private const string[] UNITS = {
        "miliarde persoane",
        "indice, 2015=100",
        "indice FAO, 2014–2016=100",
        "indice de flux, 1990=100",
        "indice 0–1",
        "indice, 2015=100",
        "indice World3, 1990=100",
        "indice de stoc, BAU 1900=100"
    };
    private const string[] SOURCES = {
        "World Bank — populație globală",
        "World Bank — industrie / populație",
        "FAOSTAT — Food, gross per capita",
        "World Bank / EDGAR — proxy CO₂",
        "UNDP — Human Development Index",
        "World Bank — producție industrială totală",
        "World3-03 — stoc persistent modelat",
        "World3-03 — resurse neregenerabile modelate"
    };
    private const string[] SOURCE_URLS = {
        "https://api.worldbank.org/v2/country/WLD/indicator/SP.POP.TOTL",
        "https://api.worldbank.org/v2/country/WLD/indicator/NV.IND.TOTL.KD",
        "https://www.fao.org/faostat/en/#data/QI",
        "https://edgar.jrc.ec.europa.eu/dataset_ghg2025",
        "https://hdr.undp.org/data-center/documentation-and-downloads",
        "https://api.worldbank.org/v2/country/WLD/indicator/NV.IND.TOTL.KD",
        "https://web.mit.edu/jsterman/www/DID.html",
        "https://web.mit.edu/jsterman/www/DID.html"
    };
    private const string[] STATUSES = {
        "Observații până în 2025; valoarea 2025 poate fi o estimare.",
        "Observațiile încep în 1992; industria include construcțiile. Graficul este per capita, nu producție totală.",
        "Observații FAOSTAT până în 2024. Puntea de observație combină 25% semnalul alimentar World3 și 75% capacitatea industrială de input; nu adaugă un feedback agricol nou.",
        "Observații până în 2024. CO₂ anual este reprezentat prin activitatea industrială; generarea și stocul de poluare persistentă rămân mecanisme latente World3 separate.",
        "Observații până în 2023; HDI nu este identic cu HWI din World3.",
        "Diagnostic observat și ancorat exact în 2025. Nu intră separat în calibrare, fiind produsul dintre populație și producția pe locuitor.",
        "Stare latentă World3, fără observație globală direct echivalentă. Arată acumularea minus asimilarea poluării persistente.",
        "Stare latentă World3, fără observație directă. Toate curbele folosesc același numitor: stocul BAU din 1900 = 100; de aceea BAU2 pornește de la 200."
    };

    private ScenarioData[] indicators;
    private Gtk.DropDown indicator_selector;
    private Gtk.DropDown horizon_selector;
    private Gtk.CheckButton uncertainty_toggle;
    private ChartView chart;
    private Gtk.Label[] card_titles;
    private Gtk.Label[] value_labels;
    private Gtk.Label[] change_labels;
    private Gtk.Label status_label;
    private Gtk.Label backtest_label;
    private Gtk.LinkButton source_button;
    private double[] backtest_reference = {};
    private double[] backtest_hybrid = {};
    private int[] backtest_start = {};
    private int[] backtest_end = {};
    private string[] multi_origins = {};
    private int[] multi_n = {};
    private double[] multi_reference = {};
    private double[] multi_hybrid = {};
    private int[] fit_start = {};
    private int[] fit_end = {};
    private double[] fit_mape = {};
    private double[] fit_bias = {};

    public MainWindow (Gtk.Application app) {
        Object (
            application: app,
            title: "World3 Empirical",
            default_width: 1180,
            default_height: 860
        );

        try {
            indicators = {};
            for (int index = 0; index < KEYS.length; index++) {
                indicators += new ScenarioData (
                    LABELS[index],
                    Path.build_filename (DATA_DIRECTORY, KEYS[index] + ".csv")
                );
            }
            load_backtests (Path.build_filename (DATA_DIRECTORY, "backtest_2019_latest.csv"));
            load_multi_origin (Path.build_filename (DATA_DIRECTORY, "backtest_multi_origin.csv"));
            load_fit_diagnostics (Path.build_filename (DATA_DIRECTORY, "fit_diagnostics.csv"));
        } catch (Error error) {
            show_startup_error (error.message);
            return;
        }

        var header = new Gtk.HeaderBar ();
        header.title_widget = build_title ();
        set_titlebar (header);

        var about_button = new Gtk.Button.from_icon_name ("help-about-symbolic");
        about_button.tooltip_text = "Metodă, surse și limite";
        about_button.clicked.connect (show_about);
        header.pack_end (about_button);

        var controls = new Gtk.Box (Gtk.Orientation.HORIZONTAL, 16);
        controls.halign = Gtk.Align.CENTER;
        controls.margin_top = 16;
        controls.margin_bottom = 6;

        indicator_selector = new Gtk.DropDown.from_strings (LABELS);
        indicator_selector.tooltip_text = "Alege indicatorul comparat";
        controls.append (labeled_control ("Indicator", indicator_selector));

        horizon_selector = new Gtk.DropDown.from_strings ({ "1960–2050", "1950–2100" });
        horizon_selector.tooltip_text = "Alege orizontul graficului";
        controls.append (labeled_control ("Orizont", horizon_selector));

        uncertainty_toggle = new Gtk.CheckButton.with_label ("Arată P10–P90");
        uncertainty_toggle.active = true;
        uncertainty_toggle.tooltip_text = "Afișează cuantilele structurale reale; linia centrală nu este forțată în interior";
        controls.append (labeled_control ("Plajă", uncertainty_toggle));

        var warning = new Gtk.Label ("");
        warning.use_markup = true;
        warning.label = "<b>BAU și BAU2</b> sunt scenariile originale. <b>BAU Hibrid 2026</b> este refitul final BAU2. Pentru hrană și CO₂ folosește două punți de observație alese numai cu date până în 2018; acestea nu înlocuiesc feedbackurile World3.";
        warning.wrap = true;
        warning.add_css_class ("dim-label");
        warning.margin_start = 24;
        warning.margin_end = 24;

        var definitions = new Gtk.Label (
            "BAU: limită mai timpurie prin resurse · BAU2: resurse mai mari, limită prin poluare · " +
            "Hibrid: o singură rulare World3 cu 7 parametri + două punți de observație fixe · selecția structurală, validarea și refitul final rămân separate"
        );
        definitions.wrap = true;
        definitions.add_css_class ("caption");
        definitions.margin_start = 24;
        definitions.margin_end = 24;
        definitions.margin_bottom = 2;

        chart = new ChartView ();
        chart.margin_start = 18;
        chart.margin_end = 18;
        chart.margin_top = 10;

        var cards = new Gtk.Box (Gtk.Orientation.HORIZONTAL, 12);
        cards.homogeneous = true;
        cards.margin_start = 18;
        cards.margin_end = 18;
        cards.margin_top = 12;
        cards.margin_bottom = 8;
        card_titles = new Gtk.Label[3];
        value_labels = new Gtk.Label[3];
        change_labels = new Gtk.Label[3];
        cards.append (build_card (0));
        cards.append (build_card (1));
        cards.append (build_card (2));

        status_label = new Gtk.Label ("");
        status_label.wrap = true;
        status_label.xalign = 0;
        status_label.add_css_class ("dim-label");

        backtest_label = new Gtk.Label ("");
        backtest_label.wrap = true;
        backtest_label.xalign = 0;
        backtest_label.add_css_class ("caption");

        source_button = new Gtk.LinkButton.with_label (SOURCE_URLS[0], SOURCES[0]);
        source_button.halign = Gtk.Align.START;

        var evidence_box = new Gtk.Box (Gtk.Orientation.VERTICAL, 3);
        evidence_box.margin_start = 24;
        evidence_box.margin_end = 24;
        evidence_box.margin_bottom = 6;
        evidence_box.append (status_label);
        evidence_box.append (backtest_label);
        evidence_box.append (source_button);

        var note = new Gtk.Label (
            "Deplasează pointerul peste grafic pentru anul exact și valorile tuturor modelelor. " +
            "Grila este la 5 ani; în orizontul 1960–2050 fiecare reper este etichetat. " +
            "Albastru întrerupt = traiectorie retrospectivă a modelului; albastru continuu = proiecție după ultima observație. " +
            "P10–P90 arată sensibilitatea celor 12 configurații admisibile, nu probabilități. " +
            "Scorul este sprijin empiric intern, nu probabilitatea ca proiecția să se realizeze. " +
            "Puntea alimentară și proxy-ul CO₂ îmbunătățesc comparația cu observațiile, dar nu sunt feedbackuri noi. " +
            "EROI, apa, clima, mineralele și AI nu sunt încă feedbackuri cuplate."
        );
        note.wrap = true;
        note.xalign = 0;
        note.add_css_class ("dim-label");
        note.margin_start = 24;
        note.margin_end = 24;
        note.margin_bottom = 18;

        var content = new Gtk.Box (Gtk.Orientation.VERTICAL, 0);
        content.append (controls);
        content.append (warning);
        content.append (definitions);
        content.append (chart);
        content.append (cards);
        content.append (evidence_box);
        content.append (note);

        var scroller = new Gtk.ScrolledWindow ();
        scroller.hscrollbar_policy = Gtk.PolicyType.NEVER;
        scroller.child = content;
        child = scroller;

        indicator_selector.notify["selected"].connect (update_view);
        horizon_selector.notify["selected"].connect (update_view);
        uncertainty_toggle.toggled.connect (update_view);
        update_view ();
    }

    private Gtk.Widget build_title () {
        var box = new Gtk.Box (Gtk.Orientation.VERTICAL, 0);
        var title_label = new Gtk.Label ("World3 Empirical");
        title_label.add_css_class ("title");
        var subtitle = new Gtk.Label ("BAU Hibrid 2026 · refit actual + validare separată");
        subtitle.add_css_class ("caption");
        subtitle.add_css_class ("dim-label");
        box.append (title_label);
        box.append (subtitle);
        return box;
    }

    private Gtk.Widget labeled_control (string text, Gtk.Widget control) {
        var box = new Gtk.Box (Gtk.Orientation.VERTICAL, 4);
        var label = new Gtk.Label (text);
        label.halign = Gtk.Align.START;
        label.add_css_class ("caption");
        label.mnemonic_widget = control;
        box.append (label);
        box.append (control);
        return box;
    }

    private Gtk.Widget build_card (int index) {
        var box = new Gtk.Box (Gtk.Orientation.VERTICAL, 5);
        box.add_css_class ("card");
        box.margin_top = 4;
        box.margin_bottom = 4;

        card_titles[index] = new Gtk.Label ("");
        card_titles[index].add_css_class ("heading");
        card_titles[index].margin_top = 12;
        box.append (card_titles[index]);

        value_labels[index] = new Gtk.Label ("");
        value_labels[index].add_css_class ("title-2");
        box.append (value_labels[index]);

        change_labels[index] = new Gtk.Label ("");
        change_labels[index].wrap = true;
        change_labels[index].add_css_class ("dim-label");
        change_labels[index].margin_bottom = 12;
        box.append (change_labels[index]);
        return box;
    }

    private void update_view () {
        int selected = (int) indicator_selector.selected;
        var data = indicators[selected];
        bool has_observations = data.has_values (ScenarioData.OBSERVED);
        int cutoff = has_observations ? data.last_observed_year () : 2025;
        chart.set_series (data, UNITS[selected], cutoff, has_observations);
        chart.set_show_uncertainty (uncertainty_toggle.active);
        if (horizon_selector.selected == 0) {
            chart.set_year_range (1960, 2050);
        } else {
            chart.set_year_range (1950, 2100);
        }

        int latest = cutoff;
        card_titles[0].label = has_observations
            ? "Ultima observație · %d".printf (latest)
            : "Stare model · %d".printf (latest);
        double latest_value = has_observations
            ? data.value_at (ScenarioData.OBSERVED, latest)
            : data.value_at (ScenarioData.HYBRID_2026, latest);
        value_labels[0].label = format_value (selected, latest_value);
        change_labels[0].label = UNITS[selected];

        int[] years = { 2030, 2035 };
        for (int card = 1; card < 3; card++) {
            int year = years[card - 1];
            double hybrid = data.value_at (ScenarioData.HYBRID_2026, year);
            double low = data.value_at (ScenarioData.P10, year);
            double high = data.value_at (ScenarioData.P90, year);
            card_titles[card].label = "BAU Hibrid 2026 · %d".printf (year);
            value_labels[card].label = format_value (selected, hybrid);
            string details = "P10–P90 structural: %s–%s".printf (
                format_value (selected, low), format_value (selected, high)
            );
            if (low.is_finite () && high.is_finite () && (hybrid < low || hybrid > high)) {
                if (hybrid < low) {
                    details += "\nCentrală cu %s sub P10".printf (
                        format_delta (selected, low - hybrid)
                    );
                } else {
                    details += "\nCentrală cu %s peste P90".printf (
                        format_delta (selected, hybrid - high)
                    );
                }
            }
            double benchmark = data.value_at (ScenarioData.BENCHMARK, year);
            if (benchmark.is_finite ()) {
                details += "\nReper ONU: " + format_value (selected, benchmark);
            }
            change_labels[card].label = details;
        }

        status_label.label = STATUSES[selected] + (has_observations
            ? " Linia roșie marchează ultima observație."
            : " Linia roșie separă simularea retrospectivă de proiecția după 2025.");
        if (selected < CALIBRATED_INDICATOR_COUNT) {
            string recent_result = backtest_hybrid[selected] <= backtest_reference[selected]
                ? "mai bun" : "mai slab";
            string multi_result = multi_hybrid[selected] <= multi_reference[selected]
                ? "mai bună" : "mai slabă";
            string bias_direction = fit_bias[selected] >= 0 ? "supraestimare" : "subestimare";
            string quality = retrospective_fit_quality (fit_mape[selected]);
            int support_score = projection_support_score (selected);
            string support = projection_support_label (support_score);
            string quality_warning = "";
            if (support_score <= 3) {
                quality_warning = " · nu susține o prognoză autonomă";
            } else if (selected == 2) {
                quality_warning = " · punte empirică, nu feedback nou";
            }
            backtest_label.label =
                "Potrivire retrospectivă după MAPE: %s · sprijin empiric intern al proiecției: %s (%d/9)%s\n".printf (
                    quality, support, support_score, quality_warning
                ) +
                "Potrivire descriptivă %d–%d · MAPE: %.2f%% · %s medie: %.2f%% · nu este holdout\n".printf (
                    fit_start[selected], fit_end[selected], fit_mape[selected],
                    bias_direction, Math.fabs (fit_bias[selected])
                ) +
                "Backtest model înghețat în 2018 · %d–%d · MAPE: %.2f%% · ancorare BAU2: %.2f%% · %s\n".printf (
                    backtest_start[selected], backtest_end[selected],
                    backtest_hybrid[selected], backtest_reference[selected], recent_result
                ) +
                "Validare multi-origin %s · n=%d ani-proiecție · MAPE procedură: %.2f%% · ancorare BAU2: %.2f%% · %s".printf (
                    multi_origins[selected], multi_n[selected],
                    multi_hybrid[selected], multi_reference[selected], multi_result
                );
        } else if (selected == 5) {
            backtest_label.label = "Diagnostic de coerență: seria este afișată și comparată cu observațiile, dar nu primește o a doua pondere în funcția de calibrare.";
        } else {
            backtest_label.label = "Diagnostic latent: nu există backtest empiric direct. Curba compară numai mecanismele BAU, BAU2 și aceeași rulare structurală hibridă.";
        }
        source_button.uri = SOURCE_URLS[selected];
        source_button.label = SOURCES[selected];
    }

    private string format_value (int indicator, double value) {
        if (indicator == 0) { return "%.2f mld.".printf (value); }
        if (indicator == 4) { return "%.3f".printf (value); }
        if (indicator == 7) { return "%.1f".printf (value); }
        return "%.1f".printf (value);
    }

    private string format_delta (int indicator, double value) {
        if (indicator == 0) { return "%.2f mld.".printf (value); }
        if (indicator == 4) { return "%.3f".printf (value); }
        return "%.1f".printf (value);
    }

    private string retrospective_fit_quality (double value) {
        if (value <= 5.0) { return "BUNĂ"; }
        if (value <= 15.0) { return "MODERATĂ"; }
        if (value <= 30.0) { return "SLABĂ"; }
        return "FOARTE SLABĂ";
    }

    private int error_points (double value, double high, double medium, double low) {
        if (value <= high) { return 3; }
        if (value <= medium) { return 2; }
        if (value <= low) { return 1; }
        return 0;
    }

    private int projection_support_score (int indicator) {
        int score = 0;
        score += error_points (fit_mape[indicator], 5.0, 15.0, 30.0);
        score += error_points (backtest_hybrid[indicator], 2.0, 5.0, 10.0);
        score += error_points (multi_hybrid[indicator], 3.0, 7.0, 15.0);

        bool recent_better = backtest_hybrid[indicator] <= backtest_reference[indicator];
        bool multi_better = multi_hybrid[indicator] <= multi_reference[indicator];

        // O procedură care pierde față de BAU2 în validarea multi-origin nu
        // poate primi calificativ ridicat, indiferent de potrivirea in-sample.
        if (!multi_better && score > 5) { score = 5; }
        // Dacă pierde în ambele teste, sprijinul este cel mult foarte limitat.
        if (!recent_better && !multi_better && score > 2) { score = 2; }
        // Punțile de observație nu sunt feedbackuri structurale noi și nu pot
        // primi singure calificativul maxim, chiar dacă validează bine.
        if (indicator == 2 && score > 7) { score = 7; }
        if (indicator == 3 && score > 4) { score = 4; }
        return score;
    }

    private string projection_support_label (int score) {
        if (score >= 8) { return "RIDICAT"; }
        if (score >= 5) { return "MODERAT"; }
        if (score >= 3) { return "LIMITAT"; }
        return "FOARTE LIMITAT";
    }

    private void load_backtests (string path) throws Error {
        string contents;
        FileUtils.get_contents (path, out contents);
        var lines = contents.split ("\n");
        for (int row = 1; row < lines.length; row++) {
            var line = lines[row].strip ();
            if (line == "") { continue; }
            var fields = line.split (",");
            if (fields.length < 7) { continue; }
            backtest_start += int.parse (fields[2]);
            backtest_end += int.parse (fields[3]);
            backtest_reference += double.parse (fields[5]);
            backtest_hybrid += double.parse (fields[6]);
        }
        if (backtest_hybrid.length != CALIBRATED_INDICATOR_COUNT) {
            throw new IOError.INVALID_DATA ("Rezultatele backtestingului sunt incomplete");
        }
    }

    private void load_multi_origin (string path) throws Error {
        string contents;
        FileUtils.get_contents (path, out contents);
        var lines = contents.split ("\n");
        for (int row = 1; row < lines.length; row++) {
            var line = lines[row].strip ();
            if (line == "") { continue; }
            var fields = line.split (",");
            if (fields.length < 7) { continue; }
            multi_origins += fields[1];
            multi_n += int.parse (fields[3]);
            multi_reference += double.parse (fields[4]);
            multi_hybrid += double.parse (fields[5]);
        }
        if (multi_hybrid.length != CALIBRATED_INDICATOR_COUNT) {
            throw new IOError.INVALID_DATA ("Backtestingul multi-origin este incomplet");
        }
    }

    private void load_fit_diagnostics (string path) throws Error {
        string contents;
        FileUtils.get_contents (path, out contents);
        var lines = contents.split ("\n");
        for (int row = 1; row < lines.length; row++) {
            var line = lines[row].strip ();
            if (line == "") { continue; }
            var fields = line.split (",");
            if (fields.length < 6) { continue; }
            fit_start += int.parse (fields[1]);
            fit_end += int.parse (fields[2]);
            fit_mape += double.parse (fields[4]);
            fit_bias += double.parse (fields[5]);
        }
        if (fit_mape.length != CALIBRATED_INDICATOR_COUNT) {
            throw new IOError.INVALID_DATA ("Diagnosticul retrospectiv este incomplet");
        }
    }

    private void show_about () {
        var dialog = new Gtk.AboutDialog ();
        dialog.transient_for = this;
        dialog.modal = true;
        dialog.program_name = "World3 Empirical";
        dialog.version = "0.10.0";
        dialog.comments =
            "BAU Hibrid 2026 compară observațiile cu scenariile World3-03 BAU și BAU2 originale. " +
            "Linia hibridă păstrează o singură rulare BAU2 cu același vector de șapte parametri structurali. Pentru comparația cu FAOSTAT, semnalul alimentar observat combină 25% ieșirea alimentară World3 și 75% capacitatea industrială de input. CO₂ anual folosește activitatea industrială drept proxy; stocul persistent de poluare rămâne separat și latent. Aceste două punți au fost alese cu date încheiate în 2018 și nu modifică selecția structurală sau feedbackurile World3. " +
            "Validarea folosește un model separat selectat numai cu date până în 2018; 2019–ultimul an rămâne test recent neatins pentru acea procedură. Linia afișată este refitul final ulterior, care folosește toate observațiile disponibile. " +
            "Perioada retrospectivă și proiecția sunt desenate distinct. Linia centrală este medoidul a 12 rulări admisibile. P10–P90 sunt cuantile autentice și nu sunt deformate pentru a include linia centrală; plaja nu este un interval probabilistic. " +
            "Sprijinul empiric intern al proiecției combină transparent potrivirea istorică, testul recent și validarea multi-origin; este plafonat când procedura pierde față de BAU2 și pentru punțile fără feedback structural propriu. " +
            "Producția industrială totală este ancorată în 2025, dar rămâne un diagnostic derivat; stocul de poluare și resursele rămase sunt stări latente. Șase parametri din șapte rămân slab identificați. " +
            "Este un scenariu experimental condițional, nu o prognoză probabilistică.";
        dialog.website = "https://doi.org/10.1111/jiec.13442";
        dialog.website_label = "Recalibrarea World3 publicată în 2024";
        dialog.license_type = Gtk.License.MIT_X11;
        dialog.authors = { "Laurentiu Staicu" };
        dialog.present ();
    }

    private void show_startup_error (string message) {
        var label = new Gtk.Label ("Datele BAU Hibrid 2026 nu au putut fi încărcate:\n" + message);
        label.wrap = true;
        label.margin_top = 30;
        label.margin_start = 30;
        label.margin_end = 30;
        child = label;
    }
}
