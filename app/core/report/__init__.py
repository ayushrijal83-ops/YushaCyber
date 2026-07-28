"""Universal Report Engine (YC-031.3).

The single entry-point for report generation across every
interactive learning module in YushaCyber.

    from app.core.report import (
        # Types
        Report, ReportSection, ReportKind, OutputFormat,
        # Builder
        ReportBuilder,
        # Models
        report_from_dict, report_from_state,
        # Templates
        get_template, template_names,
        # Services
        create_report, build_report, render_report,
        export_report, report_summary,
    )

Backward-compatible: existing report generation in SOC, Forensics,
and Blue Team modules keeps working unchanged.
"""

from app.core.report.types import (  # noqa: F401
    OutputFormat,
    Report,
    ReportKind,
    ReportSection,
    SECTION_LABELS,
    SectionKind,
)
from app.core.report.builder import ReportBuilder  # noqa: F401
from app.core.report.models import (  # noqa: F401
    report_from_dict,
    report_from_state,
)
from app.core.report.templates import (  # noqa: F401
    get_template,
    template_names,
)
from app.core.report.services import (  # noqa: F401
    build_report,
    create_report,
    export_report,
    render_report,
    report_summary,
)
