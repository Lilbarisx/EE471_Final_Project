from django.test import TestCase
from django.urls import reverse
from PIL import Image
import io
import json
from .models import UserProfile, ScanLog

class HealthTrackerTests(TestCase):
    def generate_dummy_image(self, width=100, height=100):
        file = io.BytesIO()
        image = Image.new('RGB', (width, height), color='blue')
        image.save(file, 'PNG')
        file.name = 'test.png'
        file.seek(0)
        return file

    def test_profile_get_and_post(self):
        url = reverse('profile_endpoint')
        
        # Test GET retrieves default empty profile
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['allergies'], '')
        self.assertEqual(data['medications'], '')

        # Test POST updates profile
        payload = {
            "allergies": "peanut, milk",
            "medications": "aspirin"
        }
        response = self.client.post(
            url, 
            data=json.dumps(payload), 
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['allergies'], 'peanut, milk')
        self.assertEqual(data['medications'], 'aspirin')

        # Verify DB is updated
        profile = UserProfile.objects.get(id=1)
        self.assertEqual(profile.allergies, 'peanut, milk')
        self.assertEqual(profile.current_medications, 'aspirin')

    def test_scan_logs_get_and_post(self):
        url = reverse('scan_log_endpoint')

        # Test POST creates scan log
        payload = {
            "image_url": "https://dummy.s3.amazonaws.com/scans/test.png",
            "raw_text": "Ingredients: cocoa, milk, sugar",
            "safe": True,
            "explanation": "No allergens detected"
        }
        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('id', data)

        # Test GET lists the scan logs
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        logs = response.json()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]['raw_text'], "Ingredients: cocoa, milk, sugar")
        self.assertEqual(logs[0]['safe'], True)

    def test_upload_local_fallback(self):
        url = reverse('upload_endpoint')
        
        # Test GET not allowed
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)

        # Test POST with image file uploads successfully (using local fallback since no AWS credentials exist in test env)
        img_file = self.generate_dummy_image()
        response = self.client.post(url, {'image': img_file})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('image_url', data)
        self.assertIn('/media/scans/', data['image_url'])
