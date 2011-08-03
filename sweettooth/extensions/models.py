
import os
import json
import uuid
from zipfile import ZipFile, BadZipfile

from django.core.urlresolvers import reverse
from django.contrib import auth
from django.db import models

import autoslug
import tagging
from sorl import thumbnail

# Create your models here.

class Extension(models.Model):
    name = models.CharField(max_length=200)
    uuid = models.CharField(max_length=200, unique=True, db_index=True)
    slug = autoslug.AutoSlugField(populate_from="name")
    creator = models.ForeignKey(auth.models.User, db_index=True)
    description = models.TextField()
    url = models.URLField()
    created = models.DateTimeField(auto_now_add=True)
    is_published = models.BooleanField(default=False, db_index=True)
    def __unicode__(self):
        return self.uuid

    def is_featured(self):
        try:
            tag = self.tags.get(name="featured")
            return True
        except self.tags.model.DoesNotExist:
            return False

    def get_latest_version(self):
        return self.versions.order_by("-version")[0]

tagging.register(Extension)

class InvalidExtensionData(Exception):
    pass

class ExtensionVersion(models.Model):
    extension = models.ForeignKey(Extension, related_name="versions")
    version = models.IntegerField(default=0)
    extra_json_fields = models.TextField()

    class Meta:
        unique_together = ('extension', 'version'),

    def __unicode__(self):
        return "Version %d of %s" % (self.version, self.extension)

    def make_filename(self, filename):
        return os.path.join(self.extension.uuid, str(self.version),
                            self.extension.slug + ".shell-extension.zip")

    source = models.FileField(upload_to=make_filename)

    def get_manifest_url(self, request):
        path = reverse('extensions-manifest',
                       kwargs=dict(uuid=self.extension.uuid, ver=self.pk))
        return request.build_absolute_uri(path)

    def make_metadata_json(self):
        """
        Return generated contents of metadata.json
        """
        data = json.loads(self.extra_json_fields)
        fields = dict(
            _generated  = "Generated by SweetTooth, do not edit",
            name        = self.extension.name,
            description = self.extension.description,
            url         = self.extension.url,
            uuid        = self.extension.uuid,
        )

        data.update(fields)
        return data

    def replace_metadata_json(self):
        """
        In the uploaded extension zipfile, edit metadata.json
        to reflect the new contents.
        """
        zipfile = ZipFile(self.source.storage.path(self.source.name), "a")
        metadata = self.make_metadata_json()
        zipfile.writestr("metadata.json", json.dumps(metadata, sort_keys=True, indent=2))
        zipfile.close()

    @classmethod
    def from_metadata_json(cls, metadata, extension=None):
        """
        Given the contents of a metadata.json file, create an extension
        and version with its data and return them.
        """
        if extension is None:
            extension = Extension()
            extension.name = metadata.pop('name', "")
            extension.description = metadata.pop('description', "")
            extension.url = metadata.pop('url', "")
            extension.uuid = metadata.pop('uuid', str(uuid.uuid1()))

        version = ExtensionVersion()
        version.extra_json_fields = json.dumps(metadata)

        # get version number
        ver_ids = extension.versions.order_by('-version')
        try:
            ver_id = ver_ids[0].version + 1
        except IndexError:
            # New extension, no versions yet
            ver_id = 1

        version.version = ver_id
        return extension, version

    @classmethod
    def from_zipfile(cls, uploaded_file, extension=None):
        """
        Given a file, create an extension and version, populated
        with the data from the metadata.json and return them.
        """
        try:
            zipfile = ZipFile(uploaded_file, 'r')
        except BadZipfile:
            raise InvalidExtensionData("Invalid zip file")

        try:
            metadata = json.load(zipfile.open('metadata.json', 'r'))
        except KeyError:
            # no metadata.json in archive, use web editor
            metadata = {}
        except ValueError:
            # invalid JSON file, raise error
            raise InvalidExtensionData("Invalid JSON data")

        extension, version = cls.from_metadata_json(metadata, extension)
        zipfile.close()
        return extension, version

class Screenshot(models.Model):
    extension = models.ForeignKey(Extension)
    title = models.TextField()

    def make_filename(self, filename):
        return os.path.join(self.extension.uuid, filename)

    image = thumbnail.ImageField(upload_to=make_filename)
