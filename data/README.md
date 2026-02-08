# TOEFL Essay Data

Bu klasör deneylerde kullanılacak TOEFL essay'larını ve insan puanlarını tutar.

## Dosya formatı

- **essays_template.csv** — Şablon (1 örnek satır). Kendi veriniz için bu dosyayı `essays.csv` olarak kopyalayıp doldurun:  
  `cp data/essays_template.csv data/essays.csv`
- **essays.csv** — Kendi essay veriniz (30 essay hedefi). Bu dosya `.gitignore`'da olduğu için repo'ya yüklenmez.

## Sütunlar

| Sütun         | Açıklama                                      | Örnek |
|---------------|-----------------------------------------------|-------|
| essay_id      | Benzersiz essay numarası (1, 2, 3, ...)       | 1     |
| prompt_text   | Essay sorusu / konu metni                     | Do you agree or disagree... |
| essay_text    | Öğrencinin yazdığı essay metni                | I strongly agree that... |
| human_score   | İnsan değerlendiricinin verdiği puan (0–5)    | 4     |

## Nasıl doldurulur?

1. Şablonu kopyalayın: `cp data/essays_template.csv data/essays.csv`
2. `data/essays.csv` dosyasını açın (Excel, Google Sheets veya metin editörü).
3. Her satıra bir essay ekleyin: `essay_id`, `prompt_text`, `essay_text`, `human_score`.
4. `human_score` TOEFL Independent Writing rubric'ine göre 0–5 arası tam sayı olmalı.
5. Toplamda 30 essay hedefleniyor (deney planına göre).

## Notlar

- CSV içinde çok satırlı metinler tırnak (`"`) içinde yazılır; satır sonları metin içinde kalabilir.
- `data/*.csv` ve `data/*.xlsx` `.gitignore`'da olduğu için, gerçek essay verinizi repo'ya yüklemeden yerel tutabilirsiniz. Sadece şablon/örnek commit edilir.
