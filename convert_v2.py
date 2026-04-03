import io
with io.open('test_out_v2.txt', 'r', encoding='utf-16le') as f:
    text = f.read()
with io.open('test_out_v2_utf8.txt', 'w', encoding='utf-8') as f:
    f.write(text)
