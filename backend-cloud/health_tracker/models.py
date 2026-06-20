from django.db import models

class UserProfile(models.Model):
    # comma-separated list of user allergens, e.g., "peanut, gluten, milk"
    allergies = models.TextField(blank=True, default="")
    # comma-separated list of user's active medications, e.g., "aspirin, paracetamol"
    current_medications = models.TextField(blank=True, default="")

    def __str__(self):
        return f"User Profile (Allergies: {self.allergies[:30]}...)"

class ScanLog(models.Model):
    image_url = models.URLField(max_length=500, blank=True, null=True)
    raw_text = models.TextField(blank=True, default="")
    safe = models.BooleanField(default=True)
    explanation = models.TextField(blank=True, default="")
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        status = "SAFE" if self.safe else "DANGER"
        return f"ScanLog {self.id} [{status}] at {self.timestamp}"
