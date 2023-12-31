import os
import json
import nltk
import pickle
from PIL import Image
from collections import Counter
from multiprocessing import Pool
from vocabulary import Vocabulary

nltk.download('punkt')
num_train_img = 32000
num_val_img = 4000
num_test_img = 2000
word_threshold = 4
size = [256, 256]

image_path = "./train2017" # original image
TRAIN_IMG_PATH = "./dataset/train/images" # resized image for training
VAL_IMG_PATH = "./dataset/val/images" # resized image for validation
TEST_IMG_PATH = "./dataset/test/images" # resized image for test

coco_caption_path = "./annotations/captions_train2017.json"
TRAIN_CAPTION_PATH = "./dataset/train/captions.txt"
VAL_CAPTION_PATH = "./dataset/val/captions.txt"
TEST_CAPTION_PATH = "./dataset/test/captions.txt"

VOCAB_DIR = "./dataset/vocab.pkl"

def resize_image(image_path_tuple):
    img_path, output_dir, size = image_path_tuple
    with Image.open(img_path) as img:
        resized_img = img.resize(size, Image.LANCZOS)
        resized_img.save(os.path.join(output_dir, os.path.basename(img_path)))

def process_images_in_parallel(image_paths, output_dir, size, num_processes=4):
    # 이미지 경로와 출력 디렉토리, 크기를 튜플로 묶어줍니다.
    image_path_tuples = [(img_path, output_dir, size) for img_path in image_paths]

    with Pool(num_processes) as p:
        p.map(resize_image, image_path_tuples)

def process_captions(json_file_path, img_dirs):
    # JSON 파일 읽기
    with open(json_file_path, 'r') as file:
        data = json.load(file)

    # 이미지 ID와 파일 경로 매핑
    image_file_map = {item['id']: item['file_name'] for item in data['images']}

    # 캡션 데이터를 이미지 ID별로 그룹화
    caption_groups = {}
    for item in data['annotations']:
        image_id = item['image_id']
        if image_id not in caption_groups:
            caption_groups[image_id] = []
        caption_groups[image_id].append(item['caption'].strip().replace("\n", " "))

    # 파일 이름에 따른 분류
    train_captions, val_captions, test_captions = [], [], []
    counter = Counter()

    for img_dir in img_dirs:
        file_names = set(os.listdir(img_dir))
        for image_id, file_name in image_file_map.items():
            if file_name in file_names:
                captions = caption_groups.get(image_id, [])
                for caption in captions:
                    line = f"{file_name},{caption}\n"
                    tokens = nltk.tokenize.word_tokenize(caption.lower())
                    counter.update(tokens)

                    if img_dir == img_dirs[0]:
                        train_captions.append(line)
                    elif img_dir == img_dirs[1]:
                        val_captions.append(line)
                    else:
                        test_captions.append(line)

    return train_captions, val_captions, test_captions, counter

def data_processing():
    if not os.path.exists(TRAIN_IMG_PATH):
        os.makedirs(TRAIN_IMG_PATH)
    if not os.path.exists(VAL_IMG_PATH):
        os.makedirs(VAL_IMG_PATH)
    if not os.path.exists(TEST_IMG_PATH):
        os.makedirs(TEST_IMG_PATH)
    
    images = sorted(os.listdir(image_path))
    num_images = len(images)
    
    # 이미지를 훈련, 검증, 테스트 세트로 분리
    train_images = images[:num_train_img]
    val_images = images[num_train_img:num_train_img + num_val_img]
    test_images = images[num_train_img + num_val_img:num_train_img + num_val_img + num_test_img]
    
    # 각 세트에 대한 이미지 경로를 생성
    train_image_paths = [os.path.join(image_path, image) for image in train_images]
    val_image_paths = [os.path.join(image_path, image) for image in val_images]
    test_image_paths = [os.path.join(image_path, image) for image in test_images]
    
    # 병렬 처리를 사용하여 이미지 리사이징
    process_images_in_parallel(train_image_paths, TRAIN_IMG_PATH, size, num_processes=4)
    process_images_in_parallel(val_image_paths, VAL_IMG_PATH, size, num_processes=4)
    process_images_in_parallel(test_image_paths, TEST_IMG_PATH, size, num_processes=4)
    
    # 함수 호출
    train_captions, val_captions, test_captions, counter = process_captions(coco_caption_path,[TRAIN_CAPTION_PATH, VAL_CAPTION_PATH, TEST_CAPTION_PATH])
    
    # 결과 저장
    def save_captions(captions, file_path):
        with open(file_path, 'w') as f:
            f.writelines(captions)
    
    save_captions(train_captions, TRAIN_CAPTION_PATH)
    save_captions(val_captions, VAL_CAPTION_PATH)
    save_captions(test_captions, TEST_CAPTION_PATH)
    
    # 단어 빈도에 따른 필터링
    words = [word for word, cnt in counter.items() if cnt >= word_threshold]
    
    # Vocabulary 생성 및 저장
    vocab = Vocabulary()
    vocab.add_word('<pad>')
    vocab.add_word('<start>')
    vocab.add_word('<end>')
    vocab.add_word('<unk>')  # word frequency below threshold
    
    for word in words:
        vocab.add_word(word)
    
    with open(VOCAB_DIR, 'wb') as f:
        pickle.dump(vocab, f)
    
    