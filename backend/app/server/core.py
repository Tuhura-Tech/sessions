from __future__ import annotations

from litestar.config.cors import CORSConfig
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.plugins import ScalarRenderPlugin
from litestar.plugins import CLIPluginProtocol, InitPluginProtocol

from app.db import models as m
from datetime import datetime


class ApplicationCore(InitPluginProtocol, CLIPluginProtocol):
    """Application core configuration plugin.

    This class is responsible for configuring the main Litestar application with our routes, guards, and various plugins

    """

    # __slots__ = ("app_slug",)
    # app_slug: str

    def on_app_init(self, app_config):
        """Configure application for use with SQLAlchemy.

        Args:
            app_config: The :class:`AppConfig <litestar.config.app.AppConfig>` instance.

        Returns:
            The configured app config.
        """
        from app.domains.admin.controllers import (
            AdminAttendanceController,
            AdminAttendanceStatsController,
            AdminAuthController,
            AdminBlockController,
            AdminCaregiverController,
            AdminExclusionController,
            AdminLocationController,
            AdminOccurrenceController,
            AdminSessionController,
            AdminSignupController,
            AdminStudentController,
            SessionStaffController,
            StaffController,
        )
        from app.domains.caregiver.controllers import (
            CaregiverAuthController,
            CaregiverController,
            CaregiverSignupController,
            CaregiverStudentController,
        )
        from app.domains.public.controllers import (
            HealthController,
            PublicBlockController,
            PublicSessionController,
        )
        from app.lib.settings import settings
        from app.server import plugins

        # settings = get_settings()
        # app_config.debug = settings.debug
        app_config.openapi_config = OpenAPIConfig(
            title="Tūhura Tech Sessions API",
            version="latest",
            path="/docs",
            description=("Backend API for the Tūhura Tech Sessions site.\n\n"),
            render_plugins=[ScalarRenderPlugin(version="latest")],
        )

        cors_origins = settings.cors_origins_list
        if "*" in cors_origins:
            cors_origins = [
                settings.frontend_base_url,
                settings.admin_base_url,
                "http://localhost:4321",
                "http://127.0.0.1:4321",
                "http://localhost:3002",
                "http://127.0.0.1:3002",
            ]
        cors_origins = [origin for origin in cors_origins if origin]

        app_config.cors_config = CORSConfig(
            allow_origins=cors_origins,
            allow_methods=["*"],
            allow_headers=["*"],
            allow_credentials=True,
        )

        app_config.plugins.extend(
            [
                plugins.granian,
                plugins.get_alchemy_plugin(),
                plugins.get_saq_plugin(),
                plugins.oauth2_provider,
            ],
        )

        app_config.signature_namespace.update(
            {
                # "Token": Token,
                # "OAuth2Login": OAuth2Login,
                # "RequestEncodingType": RequestEncodingType,
                # "Body": Body,
                "m": m,
                # "UUID": UUID,
                "datetime": datetime,
                # "OAuth2Token": OAuth2Token,
                # "AppSettings": AppSettings,
                # "Caregiver": m.Caregiver,
                # "AppEmailService": AppEmailService,
                # "EmailService": EmailService,
            },
        )

        app_config.route_handlers = [
            HealthController,
            PublicBlockController,
            PublicSessionController,
            CaregiverAuthController,
            CaregiverController,
            CaregiverSignupController,
            CaregiverStudentController,
            AdminAttendanceController,
            AdminAttendanceStatsController,
            AdminAuthController,
            AdminBlockController,
            AdminCaregiverController,
            AdminExclusionController,
            AdminLocationController,
            AdminOccurrenceController,
            AdminSessionController,
            AdminSignupController,
            SessionStaffController,
            StaffController,
            AdminStudentController,
        ]

        app_config.debug = True

        return app_config
