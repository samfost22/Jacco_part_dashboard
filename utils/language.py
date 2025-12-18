"""
Language and internationalization utilities.
Provides translations for Dutch and English.
"""

from typing import Dict


class Language:
    """Language translation manager."""

    # Translation dictionary
    TRANSLATIONS = {
        "en": {
            # Navigation
            "dashboard": "Dashboard",
            "job_lookup": "Job Lookup",
            "bulk_lookup": "Bulk Lookup",
            "parts_inventory": "Parts Inventory",
            "sync": "Sync Data",

            # Headers
            "eu_parts_jobs": "EU Parts Jobs Dashboard",
            "job_details": "Job Details",
            "search_jobs": "Search Jobs",

            # Status labels
            "status": "Status",
            "all_statuses": "All Statuses",
            "parts_ordered": "Parts ordered",
            "parts_delivered": "Parts delivered",
            "scheduled": "Scheduled",
            "in_progress": "In Progress",
            "completed": "Completed",
            "cancelled": "Cancelled",

            # Job fields
            "job_number": "Job Number",
            "title": "Title",
            "customer": "Customer",
            "address": "Address",
            "technician": "Technician",
            "scheduled_start": "Scheduled Start",
            "scheduled_end": "Scheduled End",
            "priority": "Priority",
            "description": "Description",
            "parts_status": "Parts Status",
            "parts_delivered_date": "Parts Delivered Date",

            # Actions
            "search": "Search",
            "filter": "Filter",
            "refresh": "Refresh",
            "export": "Export",
            "view_details": "View Details",
            "sync_now": "Sync Now",

            # Statistics
            "total_jobs": "Total Jobs",
            "active_jobs": "Active Jobs",
            "parts_pending": "Parts Pending",
            "parts_delivered_count": "Parts Delivered",
            "last_sync": "Last Sync",

            # Messages
            "no_jobs_found": "No jobs found",
            "loading": "Loading...",
            "sync_success": "Data synchronized successfully",
            "sync_failed": "Synchronization failed",
            "enter_job_number": "Enter job number",
            "job_not_found": "Job not found",

            # Map
            "show_map": "Show Map",
            "hide_map": "Hide Map",
            "location": "Location",

            # Bulk lookup
            "enter_job_numbers": "Enter job numbers (one per line)",
            "jobs_found": "jobs found",
        },

        "nl": {
            # Navigation
            "dashboard": "Dashboard",
            "job_lookup": "Klus Opzoeken",
            "bulk_lookup": "Bulk Opzoeken",
            "parts_inventory": "Onderdelen Voorraad",
            "sync": "Data Synchroniseren",

            # Headers
            "eu_parts_jobs": "EU Onderdelen Klussen Dashboard",
            "job_details": "Klus Details",
            "search_jobs": "Klussen Zoeken",

            # Status labels
            "status": "Status",
            "all_statuses": "Alle Statussen",
            "parts_ordered": "Onderdelen besteld",
            "parts_delivered": "Onderdelen geleverd",
            "scheduled": "Gepland",
            "in_progress": "In Uitvoering",
            "completed": "Voltooid",
            "cancelled": "Geannuleerd",

            # Job fields
            "job_number": "Klusnummer",
            "title": "Titel",
            "customer": "Klant",
            "address": "Adres",
            "technician": "Monteur",
            "scheduled_start": "Geplande Start",
            "scheduled_end": "Gepland Einde",
            "priority": "Prioriteit",
            "description": "Beschrijving",
            "parts_status": "Onderdelen Status",
            "parts_delivered_date": "Leveringsdatum Onderdelen",

            # Actions
            "search": "Zoeken",
            "filter": "Filteren",
            "refresh": "Vernieuwen",
            "export": "Exporteren",
            "view_details": "Bekijk Details",
            "sync_now": "Nu Synchroniseren",

            # Statistics
            "total_jobs": "Totaal Klussen",
            "active_jobs": "Actieve Klussen",
            "parts_pending": "Onderdelen In Afwachting",
            "parts_delivered_count": "Onderdelen Geleverd",
            "last_sync": "Laatste Sync",

            # Messages
            "no_jobs_found": "Geen klussen gevonden",
            "loading": "Laden...",
            "sync_success": "Data succesvol gesynchroniseerd",
            "sync_failed": "Synchronisatie mislukt",
            "enter_job_number": "Voer klusnummer in",
            "job_not_found": "Klus niet gevonden",

            # Map
            "show_map": "Toon Kaart",
            "hide_map": "Verberg Kaart",
            "location": "Locatie",

            # Bulk lookup
            "enter_job_numbers": "Voer klusnummers in (één per regel)",
            "jobs_found": "klussen gevonden",
        }
    }

    def __init__(self, language: str = "en"):
        """
        Initialize language manager.

        Args:
            language: Language code ("en" or "nl")
        """
        self.language = language if language in self.TRANSLATIONS else "en"

    def get(self, key: str, default: str = None) -> str:
        """
        Get translation for a key.

        Args:
            key: Translation key
            default: Default value if key not found

        Returns:
            Translated string
        """
        return self.TRANSLATIONS[self.language].get(key, default or key)

    def set_language(self, language: str):
        """
        Set the active language.

        Args:
            language: Language code ("en" or "nl")
        """
        if language in self.TRANSLATIONS:
            self.language = language

    def get_available_languages(self) -> Dict[str, str]:
        """
        Get available languages.

        Returns:
            Dictionary of language codes and names
        """
        return {
            "en": "English",
            "nl": "Nederlands"
        }
