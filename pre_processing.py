import json
import os
import cv2
import numpy as np
import datetime
from math import floor
import random
from builtins import any as b_any


def create_folder(p_folder_to_create):
    """
    Check if a folder exist and if not will create it
    :param p_folder_to_create:
    :return:
    """
    if not os.path.exists(p_folder_to_create):
        os.makedirs(p_folder_to_create)


def rename_real_image_with_configuration(p_root_path_real_data, p_config):
    if not os.path.exists(p_root_path_real_data):
        print("error, the folder doesn't exist :", p_root_path_real_data)
        exit(-1)
    else:
        for root, dirs, files in os.walk(p_root_path_real_data):
            if "EXCLUDE" in root:
                print("Folder exclude : ", root)
            else:
                print("Root : ", root)
                if len(files) > 0:
                    configuration = root.split("_")[1]
                    for i in range(len(files)):
                        os.rename(os.path.join(root, files[i]),
                                  os.path.join(root, files[i][0:-4] + "_" + str(configuration) + "_.png"))


def copy_resources_from_data_folder_only_if_ready(p_root_path_data, p_config):
    is_ok_found = False
    root_found = ''
    folder_list = {}
    if not os.path.exists(p_root_path_data):
        print("error, the folder doesn't exist :", p_root_path_data)
        exit(-1)
    else:
        for root, dirs, files in os.walk(p_root_path_data):
            if is_ok_found and root_found in root:
                if (b_any("distance_map" in x for x in files)
                        or b_any("_image" in x for x in files)
                        or b_any("object_index" in x for x in files)):
                    print("Currently : {}".format(root))
                    result_folder, array_path_images = subdivide_image(root, files, p_config)
                    if result_folder not in folder_list:
                        folder_list[result_folder] = []
                        folder_list[result_folder].append(array_path_images)
                    else:
                        folder_list[result_folder].append(array_path_images)

            else:
                if "OK.txt" in str(files):
                    # The file is found it means that we can process images
                    is_ok_found = True
                    root_found = root
                else:
                    is_ok_found = False
        prepare_data_for_learning(folder_list, p_config)


def subdivide_image(p_path_image, p_list_files, p_config):
    hour_folder_name = p_path_image[-24:-18]
    create_folder(os.path.join(p_config["folder_pre_processing"], hour_folder_name, "images"))
    create_folder(os.path.join(p_config["folder_pre_processing"], hour_folder_name, "ground_truth"))
    create_folder(os.path.join(p_config["folder_pre_processing"], hour_folder_name, "depth"))
    nb_sub_divide = p_config["nb_sub_divide_image"]
    folder_path = os.path.join(p_config["folder_pre_processing"],
                               hour_folder_name)
    template_image = cv2.imread(os.path.join(p_path_image, p_list_files[0]))
    height, width = template_image.shape[0], template_image.shape[1]
    array_path_image = []
    for j in range(nb_sub_divide):
        random_start_height = np.random.randint(0, height - p_config["sub_height_image"])
        random_start_width = np.random.randint(0, width - p_config["sub_width_image"])
        files_list = []
        for i in range(len(p_list_files)):
            # Make a loop on all the file
            ori_file_name = p_list_files[i]
            configuration = ori_file_name.split("_")[2]
            image_loaded = cv2.imread(os.path.join(p_path_image, ori_file_name))
            height, width = image_loaded.shape[0], image_loaded.shape[1]
            if p_config["sub_height_image"] < height and p_config["sub_width_image"] < width:
                sub_image = image_loaded[
                            random_start_height:random_start_height + p_config["sub_height_image"],
                            random_start_width:random_start_width + p_config["sub_width_image"]]
                sub_folder = ''
                object_index = False
                if "distance_map" in ori_file_name:
                    sub_folder = "depth"
                    object_index = False
                elif "object_index" in ori_file_name:
                    sub_folder = "ground_truth"
                    object_index = True
                elif "_image" in ori_file_name:
                    sub_folder = "images"
                    object_index = False

                files_names = apply_transformation_and_save(os.path.join(folder_path,
                                                                         sub_folder),
                                                            sub_image,
                                                            configuration,
                                                            object_index)
                files_list.append(files_names)
        array_path_image.append(create_tuple_data(files_list))
    return folder_path, array_path_image


def create_tuple_data(p_files_list):
    array_tuple = []
    for j in range(len(p_files_list[0])):
        array_tuple.append((p_files_list[0][j], p_files_list[1][j], p_files_list[2][j]))

    return array_tuple


def apply_transformation_and_save(p_path_image, p_sub_image, p_configuration, p_object_index):
    """
    Apply transformation on sub image in order to generate from 1 image different configuration
    :param p_path_image: path of the image for the storage
    :param p_sub_image: sub image (width, and heigth defined on the parameters)
    :param p_configuration configuration
    :param p_object_index if the object is an object index
    :return:
    """

    if p_object_index:
        p_sub_image = cv2.Canny(p_sub_image, 0, 200)

    files_paths = []
    # Original Image
    file_name = str(random.randint(0, 10000)) + "_" + datetime.datetime.now().strftime("%H%M%S%f") + "_" + str(
        p_configuration) + "_" + ".png"
    # save the original image
    exists = os.path.isfile(os.path.join(p_path_image, file_name))
    while exists:
        file_name = str(random.randint(0, 10000)) + "_" + datetime.datetime.now().strftime("%H%M%S%f") + "_" + str(
            p_configuration) + "_" + ".png"
        exists = os.path.isfile(os.path.join(p_path_image, file_name))
    if not exists:
        files_paths.append(os.path.join(p_path_image, file_name))
        cv2.imwrite(os.path.join(p_path_image, file_name), p_sub_image)

    # Flip Image

    file_name = str(random.randint(0, 10000)) + "_" + datetime.datetime.now().strftime("%H%M%S%f") + "_" + str(
        p_configuration) + "_" + ".png"
    flip_vertically = cv2.flip(p_sub_image, 0)
    exists = os.path.isfile(os.path.join(p_path_image, file_name))
    while exists:
        file_name = str(random.randint(0, 10000)) + "_" + datetime.datetime.now().strftime("%H%M%S%f") + "_" + str(
            p_configuration) + "_" + ".png"
        exists = os.path.isfile(os.path.join(p_path_image, file_name))
    if not exists:
        files_paths.append(os.path.join(p_path_image, file_name))
        cv2.imwrite(os.path.join(p_path_image, file_name), flip_vertically)

    file_name = str(random.randint(0, 10000)) + "_" + datetime.datetime.now().strftime("%H%M%S%f") + "_" + str(
        p_configuration) + "_" + ".png"
    flip_horizontally = cv2.flip(p_sub_image, 1)
    exists = os.path.isfile(os.path.join(p_path_image, file_name))
    while exists:
        file_name = str(random.randint(0, 10000)) + "_" + datetime.datetime.now().strftime("%H%M%S%f") + "_" + str(
            p_configuration) + "_" + ".png"
        exists = os.path.isfile(os.path.join(p_path_image, file_name))
    if not exists:
        files_paths.append(os.path.join(p_path_image, file_name))
        cv2.imwrite(os.path.join(p_path_image, file_name), flip_horizontally)

    file_name = str(random.randint(0, 10000)) + "_" + datetime.datetime.now().strftime("%H%M%S%f") + "_" + str(
        p_configuration) + "_" + ".png"
    flip_both = cv2.flip(p_sub_image, -1)
    exists = os.path.isfile(os.path.join(p_path_image, file_name))
    while exists:
        file_name = str(random.randint(0, 10000)) + "_" + datetime.datetime.now().strftime("%H%M%S%f") + "_" + str(
            p_configuration) + "_" + ".png"
        exists = os.path.isfile(os.path.join(p_path_image, file_name))
    if not exists:
        files_paths.append(os.path.join(p_path_image, file_name))
        cv2.imwrite(os.path.join(p_path_image, file_name), flip_both)

    # Rotation
    rows, cols = p_sub_image.shape[0], p_sub_image.shape[1]

    # rotation 90
    file_name = str(random.randint(0, 10000)) + "_" + datetime.datetime.now().strftime("%H%M%S%f") + "_" + str(
        p_configuration) + "_" + ".png"
    transformation_matrix = cv2.getRotationMatrix2D((cols / 2, rows / 2), 90, 1)
    dst = cv2.warpAffine(p_sub_image, transformation_matrix, (cols, rows))
    exists = os.path.isfile(os.path.join(p_path_image, file_name))
    while exists:
        file_name = str(random.randint(0, 10000)) + "_" + datetime.datetime.now().strftime("%H%M%S%f") + "_" + str(
            p_configuration) + "_" + ".png"
        exists = os.path.isfile(os.path.join(p_path_image, file_name))
    if not exists:
        files_paths.append(os.path.join(p_path_image, file_name))
        cv2.imwrite(os.path.join(p_path_image, file_name), dst)

    # rotation 180
    file_name = str(random.randint(0, 10000)) + "_" + datetime.datetime.now().strftime("%H%M%S%f") + "_" + str(
        p_configuration) + "_" + ".png"
    transformation_matrix = cv2.getRotationMatrix2D((cols / 2, rows / 2), 180, 1)
    dst = cv2.warpAffine(p_sub_image, transformation_matrix, (cols, rows))
    exists = os.path.isfile(os.path.join(p_path_image, file_name))
    while exists:
        file_name = str(random.randint(0, 10000)) + "_" + datetime.datetime.now().strftime("%H%M%S%f") + "_" + str(
            p_configuration) + "_" + ".png"
        exists = os.path.isfile(os.path.join(p_path_image, file_name))
    if not exists:
        files_paths.append(os.path.join(p_path_image, file_name))
        cv2.imwrite(os.path.join(p_path_image, file_name), dst)

    # rotation 270
    file_name = str(random.randint(0, 10000)) + "_" + datetime.datetime.now().strftime("%H%M%S%f") + "_" + str(
        p_configuration) + "_" + ".png"
    transformation_matrix = cv2.getRotationMatrix2D((cols / 2, rows / 2), 270, 1)
    dst = cv2.warpAffine(p_sub_image, transformation_matrix, (cols, rows))
    exists = os.path.isfile(os.path.join(p_path_image, file_name))
    while exists:
        file_name = str(random.randint(0, 10000)) + "_" + datetime.datetime.now().strftime("%H%M%S%f") + "_" + str(
            p_configuration) + "_" + ".png"
        exists = os.path.isfile(os.path.join(p_path_image, file_name))
    if not exists:
        files_paths.append(os.path.join(p_path_image, file_name))
        cv2.imwrite(os.path.join(p_path_image, file_name), dst)

    return files_paths


def create_sub_array(p_array_key, p_original_data):
    array_tuple = []
    for key in p_array_key:
        for i in range(len(p_original_data[key])):
            for j in range(len(p_original_data[key][i])):
                for k in range(len(p_original_data[key][i][j])):
                    array_tuple.append(p_original_data[key][i][j][k])
    return array_tuple


def prepare_data_for_learning(p_folder_array, p_config):
    if len(p_folder_array) < 3:
        print(
            "Can't prepare data for deep learning. "
            "Not Enough data. We need at least 3 datasets (training, validation, test")
        print("Nb folder available : ", len(p_folder_array))
        exit(-1)
    else:
        percentage_training = p_config["percentage_training"]
        percentage_validation = p_config["percentage_validation"]
        percentage_test = 100 - percentage_training - percentage_validation
        nb_folder_training = floor((len(p_folder_array) * percentage_training) / 100)
        nb_folder_test = floor((len(p_folder_array) * percentage_test) / 100)
        nb_folder_validation = len(p_folder_array) - nb_folder_training - nb_folder_test
        print("Nb of folder take for the training : ", nb_folder_training)
        print("Nb of folder take for the validation : ", nb_folder_validation)
        print("Nb of folder take for the test : ", nb_folder_test)

        keys = list(p_folder_array.keys())
        print(keys)
        random.shuffle(keys)
        sub_array_training_keys = keys[0:nb_folder_training]
        sub_array_validation_keys = keys[nb_folder_training:
                                         nb_folder_training + nb_folder_validation]
        sub_array_test_keys = keys[
                              nb_folder_training + nb_folder_validation:
                              nb_folder_training + nb_folder_validation + nb_folder_test]

        print(str(sub_array_training_keys))
        print(str(sub_array_validation_keys))
        print(str(sub_array_test_keys))

        sub_array_training = create_sub_array(sub_array_training_keys, p_folder_array)
        sub_array_validation = create_sub_array(sub_array_validation_keys, p_folder_array)
        sub_array_test = create_sub_array(sub_array_test_keys, p_folder_array)

        sub_array_training = generate_contours_above_image(sub_array_training)
        sub_array_validation = generate_contours_above_image(sub_array_validation)
        sub_array_test = generate_contours_above_image(sub_array_test)

        create_file_deep_learning_v2("training", sub_array_training, p_config)
        create_file_deep_learning_v2("validation", sub_array_validation, p_config)
        create_file_deep_learning_v2("test", sub_array_test, p_config)
		
        


def generate_contours_above_image(p_array_files) : 
    print("Generate contours Above function")
    result_array = []
    for i in range(len(p_array_files)):
        depth, image, ground_truth = p_array_files[i]
        result = create_contours_above_image(depth, ground_truth)
        if result == 0:
            result_array.append(p_array_files[i])
        if i % 1000 == 0:
            print("Progress {}/{}".format(i, len(p_array_files)))
    return result_array


def create_file_deep_learning_v2(p_name_txt_file, p_array_files, p_config):
    with open(os.path.join(p_config["folder_pre_processing"], p_name_txt_file + '.txt'),
              'w') as file_txt:
        file_txt.write(len(p_array_files) + "\n")
        for i in range(len(p_array_files)):
            depth, image, ground_truth = p_array_files[i]
            file_txt.write(
                depth.replace("\\", "\\\\") + ";" +
                image.replace("\\", "\\\\") + ";" +
                ground_truth.replace("\\", "\\\\") + ";" +
                str(image).split("_")[2] + "\n")
    file_txt.close()
    


def create_contours_above_image(p_path_depth, p_path_ground_truth):
    img = cv2.imread(p_path_ground_truth, 0)
    img_depth = cv2.imread(p_path_depth, 0)
    shapes_width, shapes_heigth = img.shape[0], img.shape[1]
    copy_edges = img.copy()
    sub_matrix = np.argwhere(copy_edges > 0)
	
    if len(sub_matrix) > (shapes_width * shapes_heigth - 1000):
        return -1
    
    if len(sub_matrix) < 25 :
        return -1
    #print(sub_matrix)	
    for i in range(len(sub_matrix)):
        row, col = sub_matrix[i]
        if 1 <= col:
            if copy_edges[col, row] > 0 and img_depth[col - 1, row] != img_depth[col, row]:
                copy_edges[col - 1, row] = 255
                copy_edges[col, row] = 0

        if col < shapes_width - 1 :
            if copy_edges[col, row] > 0 and img_depth[col + 1, row] != img_depth[col, row]:
                copy_edges[col + 1, row] = 255
                copy_edges[col, row] = 0

        if 1 <= row:
            if copy_edges[col, row] > 0 and img_depth[col, row - 1] != img_depth[col, row]:
                copy_edges[col, row - 1] = 255
                copy_edges[col, row] = 0

        if row < shapes_heigth - 1:
            if copy_edges[col, row] > 0 and img_depth[col, row + 1] != img_depth[col, row]:
                copy_edges[col, row + 1] = 255
                copy_edges[col, row] = 0
    cv2.imwrite(p_path_depth, copy_edges)
    return 0


if __name__ == '__main__':
    # Load configuration JSON file that contains all the configuration for the scenarii
    with open('config.json') as f:
        # with open('C:\\Users\\k.giroux\\Documents\\blender\\config.json') as f:
        config = json.load(f)
        print("=============================================")
        print(config)
        print("=============================================")
    root_path_data = config["root_path_data"]
    folder_name_to_create = config["folder_pre_processing"]
    create_folder(folder_name_to_create)
    if config["isRealData"]:
        rename_real_image_with_configuration(config["pathRealData"], config)
    else:
        copy_resources_from_data_folder_only_if_ready(root_path_data, config)
#    f = open("D:\\Simulator\\SimulatorPreprocessing\\training.txt", "r")
#    for x in f:
#        print(x) 
#        data = x.split(',')
#        create_contours_above_image(data[0], data[2])	
# D:\\Simulator\\SimulatorPreprocessing\\005139\\depth\\8913_164943797571_1_.png,
# D:\\Simulator\\SimulatorPreprocessing\\005139\\images\\7356_164943906962_1_.png,
# D:\\Simulator\\SimulatorPreprocessing\\005139\\ground_truth\\2280_164943922588_1_.png
#    create_contours_above_image("D:\\Simulator\\SimulatorPreprocessing\\005139\\depth\\8913_164943797571_1_.png", "D:\\Simulator\\SimulatorPreprocessing\\005139\\ground_truth\\2280_164943922588_1_.png")	

