from django.db import models
import os

class Video(models.Model):
    title = models.CharField(max_length=100)
    video_file = models.FileField(upload_to='videos/')
    subtitle_file = models.FileField(upload_to='subtitles/')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.subtitle_file.name.endswith('.srt'):
            srt_path = self.subtitle_file.path
            vtt_path = os.path.splitext(srt_path)[0] + '.vtt'
            convert_srt_to_vtt(srt_path, vtt_path)
            self.subtitle_file.name = os.path.splitext(self.subtitle_file.name)[0] + '.vtt'
            super().save(*args, **kwargs)