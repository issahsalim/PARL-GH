import os
import time
import urllib.parse
import requests
from bs4 import BeautifulSoup
from app.models import HansardFile
from django.core.management.base import BaseCommand
from app.utils.hansards_downloader import download_new_hansards



class Command(BaseCommand):
    help = "Download Hansard PDFs and save metadata to HansardFile model"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit", type=int, default=10, help="Max number of files to download"
        )

    def handle(self, *args, **options):
        count = download_new_hansards(limit=options["limit"])
        self.stdout.write(self.style.SUCCESS(f"Downloaded {count} new PDFs"))

        