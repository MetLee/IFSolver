import cv2
import os
from feature_utils import *
from urllib.parse import unquote

fast = cv2.ORB_create()
bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)


def unquote_u(string: str):
    result = unquote(string, encoding='utf-8', errors='replace')
    if '%u' in result:
        result = result.replace('%u', '\\u').encode('utf-8').decode('unicode_escape')
    return result


def cmpImage(cmpim, dlist, portal_list):
    ks, des = fast.detectAndCompute(cmpim, None)
    pic_match = []
    for idx, d in enumerate(dlist):
        matches = bf.match(des, d)
        pic_match.append({"id": idx, "matches": len(matches)})
    pic_match = sorted(pic_match, key=lambda k: k['matches'], reverse=True)

    print("Total Keys: " + str(len(ks)))
    print("Max Match Keys: " + str(pic_match[0]["id"]))
    print("Matches: " + str(pic_match[0]["matches"]))
    print("Portal Name: " + unquote_u(portal_list[pic_match[0]["id"]]["Name"]))
    print("Lat: " + portal_list[pic_match[0]["id"]]["Latitude"])
    print("Lng: " + portal_list[pic_match[0]["id"]]["Longitude"])

    store_im = cmpim.copy()
    match_im = cv2.imread("data/" + str(pic_match[0]["id"]) + ".jpg")
    matchx, matchy, _ = store_im.shape
    match_im = cv2.resize(match_im, (matchy, matchx))
    store_im = np.hstack((store_im, match_im))
    cv2.imencode('.jpg', store_im)[1].tofile(
        "cmp/" + unquote_u(portal_list[pic_match[0]["id"]]["Name"]) + ".jpg")

    valid = True
    if pic_match[0]["matches"] / len(ks) < 0.4:
        valid = False

    if not os.path.exists('Portal_Export.matched.csv'):
        with open('Portal_Export.matched.csv', 'w', encoding='utf-8') as csvfile:
            csvfile.write('Name, Latitude, Longitude, Image\n')
    with open('Portal_Export.matched.csv', 'a', encoding='utf-8') as csvfile:
        csvfile.write('"{}",{},{},"{}",0\n'.format(
            portal_list[pic_match[0]['id']]['Name'].replace('"', '""'), portal_list[pic_match[0]['id']]['Latitude'], portal_list[pic_match[0]['id']]['Longitude'], portal_list[pic_match[0]['id']]['Image']))

    return (unquote_u(portal_list[pic_match[0]["id"]]["Name"]),
            portal_list[pic_match[0]["id"]]["Latitude"],
            portal_list[pic_match[0]["id"]]["Longitude"],
            valid)


def cmpImageMain(cmpim, features):
    ks, des = fast.detectAndCompute(cmpim, None)
    matches = len(bf.match(des, features))
    total_keys = len(ks)
    if matches / total_keys < 0.75:
        return False
    else:
        return True

def get_features(pid):
    if not os.path.exists('data_feature/' + str(pid) + ".jpg.npy"):
        img = cv2.imread('data/' + str(pid) + ".jpg", 0)
        kp, des = fast.detectAndCompute(img, None)

        img_color = cv2.imread('data/' + str(pid) + ".jpg")
        for kpit in kp:
            cv2.circle(img_color, tuple(map(int, kpit.pt)), 1, (0, 0, 255), 4)
        cv2.imwrite("data_feature_preview/" + str(pid) + ".jpg", img_color)
        
        kpp, desp = pack_keypoint(kp, des)
        write_features('data_feature/' + str(pid) + ".jpg", kpp, desp)
    else:
        fr = read_features('data_feature/' + str(pid) + ".jpg.npy")
        kp, des = unpack_keypoint(fr)
    return kp, des
