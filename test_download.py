import urllib.request
import json
import time

def test_api():
    url = 'https://www.youtube.com/watch?v=jNQXAC9IVRw'
    print("[1] Requesting video details for:", url)
    
    req = urllib.request.Request(
        'http://127.0.0.1:5000/api/info',
        data=json.dumps({'url': url}).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    res = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
    print(" -> Title:", res['title'])
    print(" -> Channel:", res['channel'])
    print(" -> Duration:", res['duration_formatted'])
    print(" -> Video options:", len(res['video_options']))
    print(" -> Audio options:", len(res['audio_options']))
    
    # Test downloading Video (MP4)
    target_v_opt = res['video_options'][0]
    print(f"\n[3] Requesting download for Video: {target_v_opt['label']}...")
    
    dl_req2 = urllib.request.Request(
        'http://127.0.0.1:5000/api/download',
        data=json.dumps({
            'url': url,
            'option_id': target_v_opt['id'],
            'option_type': 'video'
        }).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    dl_res2 = json.loads(urllib.request.urlopen(dl_req2).read().decode('utf-8'))
    task_id2 = dl_res2['task_id']
    print(f" -> Task ID: {task_id2}")
    
    for _ in range(30):
        time.sleep(1)
        status_res = json.loads(urllib.request.urlopen(f'http://127.0.0.1:5000/api/progress/{task_id2}').read().decode('utf-8'))
        print(f" -> Status: {status_res['status']} | Progress: {status_res['progress']}% | Msg: {status_res.get('step_message', '')}")
        if status_res['status'] in ['completed', 'error']:
            if status_res['status'] == 'completed':
                print(f"\n[4] Video download successfully completed! Output: {status_res.get('filename')}, Size: {status_res.get('filesize_formatted')}")
            else:
                print(f"\n[4] Failed with error: {status_res.get('error')}")
            break

if __name__ == '__main__':
    test_api()

