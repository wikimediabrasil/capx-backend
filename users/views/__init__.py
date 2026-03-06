"""Aggregate exports for users.views package.

This allows imports like `from users.views import ProfileViewSet, UsersViewSet, ...`
to continue working after splitting views into multiple modules.
"""

# Account and profile views
from .account import UsersViewSet, ProfileViewSet

# Lists and tags
from .lists import QuickListViewSet, UsersBySkillViewSet, UsersByTagViewSet

# Reference data (territories, wikimedia projects, avatars)
from .reference import (
	TerritoryViewSet,
	WikimediaProjectViewSet,
	AvatarViewSet,
)

# Saved items
from .saved_items import SavedItemViewSet

# Badges
from .badges import BadgeViewSet, UserBadgeViewSet

# Statistics and recommendations
from .stats import StatisticsView, LanguagesByTerritoryView, CapacitiesByTerritoryView
from .recommendations import RecommendationView

# LetsConnect
from .letsconnect import LetsConnectViewSet

# Oauth
from .oauth import UserAuthView, AuthView, CheckView

__all__ = [
	# account
	"UsersViewSet",
	"ProfileViewSet",
	# lists
	"QuickListViewSet",
	"UsersBySkillViewSet",
	"UsersByTagViewSet",
	# reference
	"TerritoryViewSet",
	"WikimediaProjectViewSet",
	"AvatarViewSet",
	# saved items
	"SavedItemViewSet",
	# badges
	"BadgeViewSet",
	"UserBadgeViewSet",
	# stats & recs
	"StatisticsView",
	"LanguagesByTerritoryView",
	"CapacitiesByTerritoryView",
	"RecommendationView",
    # letsconnect
    "LetsConnectViewSet",
    # oauth
    "UserAuthView",
    "AuthView",
    "CheckView",
]

