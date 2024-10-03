import argparse
import cv2
import os


parser = argparse.ArgumentParser(description="Video generator.")
parser.add_argument('-p', "--path", required=True, type=str,
                    help='Path to pov object from current folder, or, if "all" is used, to the parent folder containing'
                         ' the folders of all objects. Eg: data_dumping/2024_06_14_12_47_41/ui_cd_s/109 or, if "all" '
                         'is used, data_dumping/2024_06_14_12_47_41/ui_cd_s')
parser.add_argument('-a', "--all", type=bool, help='Boolean to record the videos of all POVs at once.')
parser.add_argument('-c', "--camera", type=str,
                    help='Camera 0 (front view) is standard, but if needed, this can be changed here. Eg: 2')
opt = parser.parse_args()

folder = opt.path
if not os.path.exists(folder):
    print("Path not found.")
    exit(1)

if opt.all:
    # if all flag is active, lists all folders in the path given, generating videos for all povs
    image_folder_list = [folder[0] for folder in os.walk(folder)]
    image_folder_list.pop(0)
else:
    # else, considers just the folder in the path given (the pov folder)
    image_folder_list = [folder]

for image_folder in image_folder_list:
    # iterates through pov folders
    folder_names = image_folder.split("/")
    parent_folder = f"videos/{folder_names[-3]}"
    if not os.path.exists(parent_folder):
        os.makedirs(parent_folder)

    if opt.camera is not None:
        # if camera argument has been given, considers the images for the chosen camera
        video_name = f"{parent_folder}/{folder_names[-2]}_{folder_names[-1]}_cam{str(opt.camera)}.mp4"
        image_file_suffix = f"_camera{str(opt.camera)}.png"
    else:
        # otherwise, considers only the images for the frontal camera (cam0)
        video_name = f"{parent_folder}/{folder_names[-2]}_{folder_names[-1]}_cam0.mp4"
        image_file_suffix = "_camera0.png"

    print(f"Generating {video_name}...")
    file_list = os.listdir(image_folder)
    file_list.sort()

    # list comprehension for all images within the current folder that relate to the chosen camera
    images = [img for img in file_list if img.endswith(image_file_suffix)]
    frame = cv2.imread(os.path.join(image_folder, images[0]))
    height, width, layers = frame.shape

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")  # mp4 videos have lower file size without compromising on quality
    video = cv2.VideoWriter(video_name, fourcc, 10, (width, height))  # video created at 10 fps

    # iterate through images, writing the frames to the video
    for image in images:
        video.write(cv2.imread(os.path.join(image_folder, image)))

    cv2.destroyAllWindows()
    video.release()

print("All videos generated.")
