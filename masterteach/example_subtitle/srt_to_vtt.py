def convert_srt_to_vtt(srt_path, vtt_path):
    with open(srt_path, 'r', encoding='utf-8') as srt_file:
        srt_content = srt_file.read()
    
    vtt_content = "WEBVTT\n\n" + srt_content.replace(',', '.')
    
    with open(vtt_path, 'w', encoding='utf-8') as vtt_file:
        vtt_file.write(vtt_content)