from functools import cache

from advanced_alchemy.extensions.litestar import SQLAlchemyPlugin
from litestar_granian import GranianPlugin
from litestar_saq import SAQPlugin
from app.lib.settings import saq_settings, _get_sqlalchemy_settings
from app.utils.oauth import OAuth2ProviderPlugin


# Create alchemy plugin lazily to avoid initializing DB engine at import time
def _get_alchemy_plugin() -> SQLAlchemyPlugin:
    """Get SQLAlchemy plugin lazily."""
    return SQLAlchemyPlugin(config=_get_sqlalchemy_settings())


@cache
def get_alchemy_plugin() -> SQLAlchemyPlugin:
    """Get SQLAlchemy plugin with caching."""
    return _get_alchemy_plugin()


granian = GranianPlugin()
oauth2_provider = OAuth2ProviderPlugin()


@cache
def get_saq_plugin() -> SAQPlugin:
    """Get SAQ plugin lazily to avoid Redis connection during build."""
    return SAQPlugin(config=saq_settings)
