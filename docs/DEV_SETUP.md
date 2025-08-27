# Development Setup

## WeasyPrint on Windows

WeasyPrint depends on the Cairo, Pango, and GDK-PixBuf libraries. On Windows:

1. Install the [GTK3 runtime for Windows](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases).
2. Add the GTK\bin directory to your `PATH`.
3. Install Python dependencies: `pip install -r backend/requirements.txt`.

Without these libraries, PDF rendering with WeasyPrint will fail. The application will fall back to the legacy ReportLab renderer when the `USE_HTML_TEMPLATE_INVOICE` environment variable is not set to `1`.
