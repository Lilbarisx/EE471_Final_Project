import os
import uuid
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import UserProfile, ScanLog

@csrf_exempt
def profile_endpoint(request):
    profile, created = UserProfile.objects.get_or_create(id=1)
    
    if request.method == 'GET':
        return JsonResponse({
            "allergies": profile.allergies,
            "medications": profile.current_medications
        })
        
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            profile.allergies = data.get('allergies', '').strip()
            profile.current_medications = data.get('medications', '').strip()
            profile.save()
            return JsonResponse({
                "status": "success",
                "allergies": profile.allergies,
                "medications": profile.current_medications
            })
        except Exception as e:
            return JsonResponse({"error": f"Invalid data format: {str(e)}"}, status=400)
            
    return JsonResponse({"error": "Method not allowed"}, status=405)

@csrf_exempt
def upload_endpoint(request):
    if request.method != 'POST':
        return JsonResponse({"error": "Only POST requests are allowed"}, status=405)
        
    image_file = request.FILES.get('image') or request.FILES.get('file')
    if not image_file:
        return JsonResponse({"error": "No image file provided"}, status=400)
        
    aws_key = os.environ.get('AWS_ACCESS_KEY_ID')
    aws_secret = os.environ.get('AWS_SECRET_ACCESS_KEY')
    bucket_name = os.environ.get('AWS_STORAGE_BUCKET_NAME')
    
    try:
        if aws_key and aws_secret and bucket_name:
            # AWS S3 Upload
            import boto3
            s3 = boto3.client(
                's3',
                aws_access_key_id=aws_key,
                aws_secret_access_key=aws_secret,
                region_name=os.environ.get('AWS_REGION', 'us-east-1')
            )
            file_name = f"scans/{uuid.uuid4()}_{image_file.name}"
            content_type = image_file.content_type or 'image/png'
            
            s3.upload_fileobj(
                image_file,
                bucket_name,
                file_name,
                ExtraArgs={'ACL': 'public-read', 'ContentType': content_type}
            )
            image_url = f"https://{bucket_name}.s3.amazonaws.com/{file_name}"
        else:
            # Local Storage Fallback
            from django.core.files.storage import default_storage
            file_path = f"scans/{uuid.uuid4()}_{image_file.name}"
            saved_path = default_storage.save(file_path, image_file)
            image_url = request.build_absolute_uri(settings.MEDIA_URL + saved_path)
            
        return JsonResponse({
            "status": "success",
            "image_url": image_url
        })
    except Exception as e:
        return JsonResponse({"error": f"Upload failed: {str(e)}"}, status=500)

@csrf_exempt
def scan_log_endpoint(request):
    if request.method == 'GET':
        logs = ScanLog.objects.all().order_by('-timestamp')
        log_list = []
        for log in logs:
            log_list.append({
                "id": log.id,
                "image_url": log.image_url,
                "raw_text": log.raw_text,
                "safe": log.safe,
                "explanation": log.explanation,
                "timestamp": log.timestamp.isoformat()
            })
        return JsonResponse(log_list, safe=False)
        
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            log = ScanLog.objects.create(
                image_url=data.get('image_url', ''),
                raw_text=data.get('raw_text', ''),
                safe=data.get('safe', True),
                explanation=data.get('explanation', '')
            )
            return JsonResponse({
                "status": "success",
                "id": log.id,
                "timestamp": log.timestamp.isoformat()
            })
        except Exception as e:
            return JsonResponse({"error": f"Invalid data format: {str(e)}"}, status=400)
            
    return JsonResponse({"error": "Method not allowed"}, status=405)
