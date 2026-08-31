public class World3Empirical.Application : Gtk.Application {
    public Application () {
        Object (
            application_id: "io.github.laurentiustaicu.World3Empirical",
            flags: ApplicationFlags.DEFAULT_FLAGS
        );
    }

    protected override void activate () {
        var existing = active_window;
        if (existing != null) {
            existing.present ();
            return;
        }

        var window = new MainWindow (this);
        window.present ();
    }

    public static int main (string[] args) {
        return new Application ().run (args);
    }
}

