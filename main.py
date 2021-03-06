from multiprocessing.pool import ThreadPool
import cv2
from os import path, makedirs
import json

from feature_utils import *
from download_utils import *
from img_finder import *
from img_cmp import *
from geo import geo

def create_dir():
    if not path.exists('data'):
        os.makedirs('data')
    if not path.exists('data_feature'):
        os.makedirs('data_feature')
    if not path.exists('data_feature_preview'):
        os.makedirs('data_feature_preview')
    if not path.exists('cmp'):
        os.makedirs('cmp')
    if not path.exists('combine'):
        os.makedirs('combine')

def main_download():
    print("[IFSolver] Downloading latest intel package")
    portal_list = getPortals("Portal_Export.csv")
    run = ThreadPool(12).imap_unordered(fetch_url, portal_list)
    for res in run:
        if res != "":
            print(res)
    return portal_list

def main_features(portal_list):
    print("[IFSolver] Getting Features")
    dlist = []
    for portal in portal_list:
        _, d = get_features(portal['id'])
        dlist.append(d)
    if not path.exists("ifs.jpg"):
        print("[IFSolver] No IFS jpg found, exit")
        exit()
    return dlist

def main_preextract(mat_size=2, thres=5):
    psf = process_mainfile(mat_size, thres)
    print("Matrix Size: " + str(mat_size))
    print("Thres: " + str(thres))
    p = input("Please check result_pre.jpg, is it correct? (y/n)")
    if p != "y":
        mat_size = input("New Matrix Size: ")
        thres = input("New Thres: ")
        return main_preextract(mat_size, thres)
    else:
        return psf

def main_extract(img,cnts):
    print("[IFSolver] Extracting pictures")
    row = {}
    bds = []
    for idx, f in enumerate(cnts):
        (x, y, w, h) = cv2.boundingRect(f)
        if (w*h > 40000):
            bds.append({"idx": idx, "bd": (x, y, w, h)})
    return img, bds, row

def main_fix():
    img, cnts = main_preextract()
    return main_extract(img, cnts)

def main():
    portal_list = main_download()
    dlist = main_features(portal_list)
    img, bds, row = main_fix()
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
    print("[IFSolver] Comparing pictures")

    main_combined = []
    fast = cv2.ORB_create()
    for idx, f in enumerate(bds):
        (x, y, w, h) = f['bd']
        found = False
        for j, item in enumerate(main_combined):
            if cmpImageMain(img_gray[y: y + h, x: x + w], item['d']):
                bds[idx]['combined_number'] = j
                found = True
                matchx, matchy, _ = item['image'].shape #
                resize_img = cv2.resize(
                    img[y: y + h, x: x + w], (matchy, matchx))
                main_combined[j]['result_image'] = np.hstack(
                    (item['result_image'], resize_img))
                main_combined[j]['combined'] = True
                break
        if not found:
            _, d = fast.detectAndCompute(img_gray[y: y + h, x: x + w], None)
            bds[idx]['combined_number'] = len(main_combined)
            # main_combined.append(
            #     {'d': d, 'image': img[y: y + h, x: x + w])
            main_combined.append(
                {'d': d, 'image': img[y: y + h, x: x + w], 'result_image': img[y: y + h, x: x + w].copy(), 'combined': False})

        print('\rCombining ' + str(idx) + '/' + str(len(bds) - 1), end='', flush=True)
        if found:
            print(' Found    ', end='', flush=True)
        else:
            print(' Not Found', end='', flush=True)

    print('')
    print('----------------------------')
    print('Individual pictures: ' + str(len(main_combined)))
    print('----------------------------')

    for idx, group_combine in enumerate(main_combined):
        if group_combine['combined']:
            cv2.imencode('.jpg', group_combine['result_image'])[1].tofile("combine/" + str(idx) + ".jpg") 

    for idx, item in enumerate(main_combined):
        print('Result for combined pic ' + str(idx))
        pname, lat, lng, valid = cmpImage(item['image'], dlist, portal_list)
        main_combined[idx]['result'] = (pname, lat, lng, valid)
        print('----------------------------')

    for idx, f in enumerate(bds):
        (x, y, w, h) = f["bd"]
        print("\rResult for pic " + str(idx), end='', flush=True)
        (pname, lat, lng,
         valid) = main_combined[bds[idx]['combined_number']]['result']

        if valid:
            cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 5)
            cv2.putText(img, 'Lat: ' + lat, (x, y + 40),
                        cv2.FONT_HERSHEY_COMPLEX, 1, (0, 0, 255), 2)
            cv2.putText(img, 'Lng: ' + lng, (x, y + 80),
                        cv2.FONT_HERSHEY_COMPLEX, 1, (0, 0, 255), 2)
        if str(round((x+0.5*w)/100)) not in row.keys():
            row[str(round((x+0.5*w)/100))] = [{
                "id": idx,
                "name": pname,
                "x": x,
                "x+0.5w": x+0.5*w,
                "y": y/100,
                "lat": lat,
                "lng": lng,
                "valid": valid
            }]
        else:
            row[str(round((x+0.5*w)/100))].append({
                "id": idx,
                "name": pname,
                "x": x,
                "x+0.5w": x+0.5*w,
                "y": y/100,
                "lat": lat,
                "lng": lng,
                "valid": valid
            })
    print('')

    for k in row.keys():
        row[k] = sorted(row[k], key=lambda kk: kk['y'])
    with open('result.json', 'w') as fp:
        json.dump(row, fp, sort_keys=True)
    cv2.imwrite("result.jpg", img)
    print("[IFSolver] Doing geograpjical image generation")
    geo()

if __name__ == "__main__":
    create_dir()
    main()
