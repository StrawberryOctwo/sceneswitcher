from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponseNotFound, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from django.conf import settings
from django.contrib.auth.decorators import login_required
import datetime, os
import shutil
from .test import *
from pathlib import Path
import logging
import os
import shutil
from pathlib import Path
import uuid
from .models import Package
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.cache import cache

def generate_unique_id():
    return str(uuid.uuid4())


def generate_datetime_alias():
    current_time = datetime.datetime.now()
    return current_time.strftime("%Y-%m-%d_%H-%M-%S")


def save_font_params(
    font_size, font_color, bg_color, margin, font_file_path, file_path
):
    params_string = f"{font_size};{font_color};{bg_color};{margin};{font_file_path}"
    with open(file_path, "w") as f:
        f.write(params_string)


def load_font_params(file_path):
    try:
        with open(file_path, "r") as f:
            params_string = f.read()
            font_size, font_color, bg_color, margin, font_file_path = (
                params_string.split(";")
            )
            return int(font_size), font_color, bg_color, int(margin), font_file_path
    except Exception as e:
        return None

from sceneswitcher.forms import ContactUsForm
def index(request):
    if request.user.is_authenticated:
        return redirect("app")
    contact_us_form = ContactUsForm(request.POST or None)
    if request.method == "POST":
        if contact_us_form.is_valid():
            print(contact_us_form.cleaned_data)
            try:
                sendded = contact_us_form.send()
                
            except Exception as e:
                messages.error(request, "An error occurred while sending the message")
                print(e)
            messages.success(request, "Message sent successfully")
            return redirect("index")
    
    packages = Package.objects.all().order_by("price")
    context = {
        "basic": packages[0],
        "professional": packages[1],
        "premium": packages[2],
        "contact_us_form": contact_us_form,
    }

    return render(request, "index.html", context=context)


@login_required
def download(request):
    return render(request, "download.html")


@login_required
def app(request):
    return render(request, "backend.html")


@login_required
def video_processing_page(request):
    return render(request, "video_processing.html")


def get_srt_index(request):
    current_time = float(request.GET["time"])
    subtitles = load_subtitles_from_file(Path("media/uploads/original_subtitles.srt"))

    # Iterate over the subtitles to find which one matches the current time
    for index, subtitle in enumerate(subtitles):
        start_time = subriptime_to_seconds(subtitle.start)
        end_time = subriptime_to_seconds(subtitle.end)
        if start_time <= current_time <= end_time:
            return JsonResponse({"srt_index": index})

    return JsonResponse({"srt_index": -1})  # Return -1 if no matching subtitle is found


def process_multiple_video_segment_replacements(
    original_video_path,
    subtitles_path,
    replacements,
    font_path,
    font_size,
    font_color,
    bg_color,
    margin,
):
    # Load original video and subtitles
    video = load_video_from_file(Path(original_video_path))
    subtitles = load_subtitles_from_file(Path(subtitles_path))
    timestamps = split_by_computer_vision(Path(original_video_path))

    for ts in timestamps:
        if ts["confidence"] > MAE_THRESHOLD:
            logging.debug(
                f"Frame: {ts['frame_number']}, Timestamp: {ts['timestamp']}, Confidence: {ts['confidence']}"
            )
    logging.info("Video loaded successfully")
    cropped_video = crop_to_aspect_ratio(video, 4 / 5)
    logging.info("Video cropped to desired aspect ratio")

    refined_subtitles = refine_subtitles_based_on_computer_vision(
        subtitles, timestamps, replacements
    )
    refined_srt_file = Path(subtitles_path).with_name(
        Path(subtitles_path).stem + "_refined.srt"
    )

    # Save the refined subtitles
    refined_subtitles.save(refined_srt_file)
    logging.info(f"Refined subtitles saved to {refined_srt_file}")

    # Attempt to move the refined SRT file to the final location
    try:
        final_srt_path = os.path.join("media/uploads", "original_subtitles.srt")
        shutil.move(refined_srt_file, final_srt_path)
        logging.info(f"Moved refined SRT file to {final_srt_path}")
    except FileNotFoundError as e:
        logging.error(f"Error moving refined SRT file: {e}")
        raise

    # Segment the original video based on the subtitles
    video_segments, subtitle_segments = get_segments_using_srt(video, refined_subtitles)

    # Process each replacement
    for replacement in replacements:
        srt_index = replacement["srt_index"]
        replacement_video_path = replacement["scene_path"]

        # Load the replacement video segment
        replacement_video = load_video_from_file(Path(replacement_video_path))
        cropped_replacement_video = crop_to_aspect_ratio(
            replacement_video, video.aspect_ratio
        )

        # Replace the specific segment in the video
        video_segments[srt_index] = replace_video_segments(
            video_segments,
            {srt_index: cropped_replacement_video},
            subtitles,
            video,
            font_path,
            font_size,
            font_color,
            bg_color,
            margin,
        )[
            srt_index
        ]  # only replace the specific segment

    # Concatenate the updated video segments into a final video
    final_video = concatenate_videoclips(video_segments)
    original_audio = video.audio.subclip(0, final_video.duration)
    final_video_with_audio = final_video.set_audio(original_audio)

    # Save the final video with all the replaced segments
    temp_final_video_path = Path("media/uploads") / "temp_final_video.mp4"
    final_video_with_audio.write_videofile(
        temp_final_video_path.as_posix(), codec="libx264", audio_codec="aac"
    )

    # Replace the original video with the new one
    os.remove(original_video_path)  # Remove the old file
    temp_final_video_path.rename(
        original_video_path
    )  # Rename temp file to original path

    video = VideoFileClip(original_video_path)
    watermark = ImageClip("static/assets/logo.png")
    watermark = watermark.resize(height=50)
    watermark = watermark.set_position("center").set_duration(video.duration)
    watermark_video = CompositeVideoClip([video, watermark])
    directory, filename = os.path.split(original_video_path)
    new_filename = f"watermark_{filename}"
    watermark_path = os.path.join(directory, new_filename)
    if os.path.exists:
        os.remove(watermark_path)
    watermark_video.write_videofile(
        watermark_path, codec="libx264", audio_codec="aac", threads=4
    )

    return HttpResponse("Success")


@csrf_exempt
def process_video(request):
    if request.method == "POST":
        original_video_path = "media/uploads/original_video.mp4"
        subtitles_path = "media/uploads/original_subtitles.srt"

        # Load all replacements from session
        replacements = request.session.get("replacements", [])
        # Ensure we have replacements to process
        if not replacements:
            return HttpResponse("No segments to replace", 400)

        font_params_file = os.path.join("media/uploads", "font_params.txt")
        font_size, font_color, bg_color, margin, font_file_path = load_font_params(
            font_params_file
        )
        # Process all replacements
        process_multiple_video_segment_replacements(
            original_video_path=original_video_path,
            subtitles_path=subtitles_path,
            replacements=replacements,
            font_path=font_file_path,
            font_size=int(font_size),
            font_color=str(font_color),
            bg_color=str(bg_color),
            margin=int(margin),
        )

        # Clear the session replacements after processing
        if "replacements" in request.session:
            del request.session["replacements"]

        return HttpResponse("Successful")
    return render(request, "loading.html")


@login_required
def process(request):
    if request.method == "POST":
        static_out_file_server = os.path.join("static", "output_root")
        tmp = os.path.join(os.getcwd(), "media/tmp")
        upload_folder = os.path.join(os.getcwd(), "media/uploads")
        final_out_path = os.path.join("static", "output_root", "final")
        outpath = os.path.join(static_out_file_server, "output")

        try:
            # Cleanup old files
            remove_all_files_in_directory(os.path.join(upload_folder))
            remove_all_files_in_directory(os.path.join(outpath, "videos"))
            remove_all_files_in_directory(os.path.join(outpath, "audios"))
            remove_all_files_in_directory(final_out_path)

            if os.path.exists(tmp):
                tmp_dirs = os.listdir(tmp)
                for dir in tmp_dirs:
                    remove_all_files_in_directory(os.path.join(tmp, dir))
                remove_all_files_in_directory(tmp)
        except Exception as e:
            return JsonResponse(
                {
                    "status": "error",
                    "message": f"An error occurred during cleanup: {e}",
                },
                status=500,
            )

        try:
            # Create necessary directories
            os.makedirs(outpath, exist_ok=True)
            os.makedirs(os.path.join(outpath, "audios"), exist_ok=True)
            os.makedirs(os.path.join(outpath, "videos"), exist_ok=True)
            os.makedirs(final_out_path, exist_ok=True)
            os.makedirs(tmp, exist_ok=True)  # Ensure the tmp directory exists
            os.makedirs(upload_folder, exist_ok=True)  # Ensure the tmp directory exists
        except Exception as e:
            return JsonResponse(
                {
                    "status": "error",
                    "message": f"An error occurred during directory creation: {e}",
                },
                status=500,
            )

        unique_special_id = os.path.join(tmp, generate_unique_id())

        video_dir = os.path.join(unique_special_id, "video")
        clips_dir = os.path.join(unique_special_id, "clips")
        mp3_dir = os.path.join(unique_special_id, "mp3")
        text_dir = os.path.join(unique_special_id, "text")
        font_dir = os.path.join(unique_special_id, "font")
        os.makedirs(video_dir, exist_ok=True)
        os.makedirs(clips_dir, exist_ok=True)
        os.makedirs(mp3_dir, exist_ok=True)
        os.makedirs(text_dir, exist_ok=True)
        os.makedirs(font_dir, exist_ok=True)

        try:
            # Save uploaded files
            video_file = request.FILES["video_file"]
            mp3_file = request.FILES["mp3_file"]
            text_file = request.FILES["text_file"]
            font_file = request.FILES["font_file"]

            if not video_file or not mp3_file or not text_file or not font_file:
                return JsonResponse(
                    {"status": "error", "message": "Missing required files"}, 400
                )

            video_file_path = os.path.join(video_dir, video_file.name)
            mp3_file_path = os.path.join(mp3_dir, mp3_file.name)
            text_file_path = os.path.join(text_dir, text_file.name)
            font_file_path = os.path.join(font_dir, font_file.name)

            """video_file.save(video_file_path)
			mp3_file.save(mp3_file_path)
			text_file.save(text_file_path)
			font_file.save(font_file_path)
			"""
            save_file(mp3_file_path, mp3_file)
            save_file(text_file_path, text_file)
            save_file(font_file_path, font_file)
            save_file(video_file_path, video_file)

        except Exception as e:
            return JsonResponse(
                {
                    "status": "error",
                    "message": f"An error occurred while saving files: {e}",
                },
                500,
            )
        # New parameters
        font_size = int(request.POST.get("font_size", 20))
        font_color = str(request.POST.get("font_color"))
        bg_color = str(request.POST.get("bg_color"))
        margin = int(request.POST.get("margin", 26))

        font_params_file = os.path.join("media/uploads", "font_params.txt")
        save_font_params(
            font_size, font_color, bg_color, margin, font_file_path, font_params_file
        )

        # Generate the SRT file from TXT and MP3 files
        try:
            srt_file = generate_srt_from_txt_and_audio(
                Path(text_file_path), Path(mp3_file_path), Path(tmp)
            )
        except Exception as e:
            return JsonResponse(
                {"status": "error", "message": f"Failed to generate SRT file: {e}"}, 500
            )

        # Move the SRT file to uploads directory for further processing
        final_srt_path = os.path.join("media/uploads", "original_subtitles.srt")
        shutil.move(srt_file, final_srt_path)

        # Move the video file to uploads directory for further processing
        final_video_path = os.path.join("media/uploads", "original_video.mp4")
        if os.path.exists(os.path.join("media/uploads", "original_video.mp4")):
            os.remove(os.path.join("media/uploads", "original_video.mp4"))
        shutil.move(video_file_path, final_video_path)
        video = VideoFileClip(final_video_path).resize(height=720)
        watermark_path = os.path.join("media/uploads", "watermark_original_video.mp4")
        watermark = ImageClip("static/images/watermark.png")
        watermark = watermark.resize(height=280, width=280)
        watermark = watermark.set_position("center").set_duration(video.duration)
        watermark_video = CompositeVideoClip([video, watermark])
        if os.path.exists(watermark_path):
            os.remove(watermark_path)
        watermark_video.write_videofile(
            watermark_path, codec="libx264", audio_codec="aac", threads=4
        )
        # Return JSON response with success message
        response = {
            "status": "success",
            "message": "Files processed successfully",
            "redirect": reverse("video_processing"),
        }
        return JsonResponse(response)


def save_file(file_path, file):
    with open(file_path, "wb") as f:
        f.write(file.read())


def remove_all_files_in_directory(directory):
    if os.path.exists(directory):
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                return None


@login_required
def load_media_file(request, file_name):
    try:
        file_path = os.path.join(settings.MEDIA_ROOT, "uploads/" + file_name)
        directory, filename = os.path.split(file_path)
        new_filename = f"watermark_{filename}"
        watermark_path = os.path.join(directory, new_filename)
        if os.path.exists(watermark_path):
            file_path = watermark_path
        with open(file_path, "rb") as f:
            content = f.read()
            content_type = "video/mp4"  #'application/octet-stream'
            response = HttpResponse(content, content_type=content_type)
            response["Content-Disposition"] = (
                f'attachment; filename="{os.path.basename(file_path)}"'
            )
            response["Accept-Ranges"] = "bytes"
            return response
    except Exception:
        return HttpResponseNotFound("File not found.")


@login_required
def load_final_media_file(request, file_name):
    try:
        user = request.user
        user.credits -= 1
        user.save()
        file_path = os.path.join(settings.MEDIA_ROOT, "uploads/" + file_name)
        with open(file_path, "rb") as f:
            content = f.read()
            content_type = "video/mp4"  #'application/octet-stream'
            response = HttpResponse(content, content_type=content_type)
            response["Content-Disposition"] = (
                f'attachment; filename="{os.path.basename(file_path)}"'
            )
            response["Accept-Ranges"] = "bytes"
            return response

    except Exception:
        return HttpResponseNotFound("File not found.")


@csrf_exempt
def upload_new_scene(request):
    if request.method == "POST":
        srt_index = int(request.POST["srt_index"])
        new_scene = request.FILES["scene"]

        temp_scene_path = os.path.join("media/uploads", new_scene.name)
        save_file(temp_scene_path, new_scene)

        # Store the replacement details in session
        if "replacements" not in request.session:
            request.session["replacements"] = []

        if not any(
            r["srt_index"] == srt_index for r in request.session["replacements"]
        ):
            request.session["replacements"].append(
                {"srt_index": srt_index, "scene_path": temp_scene_path}
            )
            request.session.modified = True
            request.session["replacements"] = request.session["replacements"]

        return HttpResponse("Scene uploaded and stored for replacement.")

from django.core.mail import send_mail
from django.contrib.auth import login
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
def send_confirmation_email(email, name):
    # HTML email content
    logi_url = settings.DOMAIN + 'login'
    html_content = f"""
    <html>
    <body>
        <p>Hi {name},</p>
        <p>Thank you for joining <strong>SceneSwitcher.io</strong>! Now, you can easily swap scenes and combat ad fatigue in your VSLs.</p>

        <h4>Next Steps:</h4>
        <ol>
            <li><strong>Log in:</strong> Login to SceneSwitcher.io</li>
            <li><strong>Get Started:</strong> Upload your VSL and start creating variations.</li>
            <li><strong>Need Assistance?</strong> Email us at support@sceneswitcher.io.</li>
        </ol>

        <p>Let’s refresh your content and boost conversions!</p>
        <p><strong><a>{logi_url} </a> </strong></p>
        <p>Best, <br>The SceneSwitcher.io Team</p>
    </body>
    </html>
    """

    email_message = EmailMessage(
        subject="Welcome to SceneSwitcher.io – Time to Refresh Your VSLs!",
        body=html_content,
        from_email=settings.EMAIL_HOST_USER,
        to=[email],
    )
    email_message.content_subtype = "html"  # This is required to send the email as HTML
    email_message.send(fail_silently=False)
    
User = get_user_model()
def set_password(request):

    if request.method == "POST":
        token = request.GET.get("t")
        print(token)
        print(cache.get(token))
        if cache.get(token):
            user_id = cache.get(token)
            user = User.objects.get(id=user_id)
        else:
            return redirect("login")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")
        email = request.POST.get("email")
        if password1 and password2 and password1 == password2:
            # user = User.objects.get()
            user.set_password(password1)
            # make sure email is unique
            user.email = email
            try:
                user.save()
            except:
                messages.error(request, "Email already exists")
                return render(request, "registration/set_password.html")
            cache.delete(token)
            login(request, user)
            send_confirmation_email(email, user.first_name)
            return redirect("app")
        else:
            messages.error(request, "Passwords do not match")
            return render(request, "registration/set_password.html")

    elif request.method == "GET":
        if cache.get(request.GET.get("t")):
            return render(request, "registration/set_password.html")
            
    return redirect("login")


