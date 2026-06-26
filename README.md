---
title: SkyWise
emoji: 🌤
colorFrom: indigo
colorTo: blue
sdk: gradio
sdk_version: "5.0.0"
app_file: app.py
pinned: false
---

# ◐ SkyWise — Hava Durumuna Göre Aktivite Asistanı

SkyWise, bulunduğun (ya da gideceğin) şehrin **hava durumunu analiz edip** sana en uygun
aktiviteleri öneren, Türkçe/İngilizce konuşan bir AI asistandır. Çekirdek ilkesi: **hava her
zaman birinci** — bir aktivite havaya uymuyorsa, sevsen bile olduğu gibi önerilmez; güvenli
bir alternatif sunulur. Tercihlerini (tarayıcına özel) hatırlayarak zamanla daha kişisel öneriler verir.

> Gradio arayüzü · LangGraph ReAct ajan + supervisor · OpenAI (gpt-4o-mini) · OpenWeatherMap +
> Open-Meteo + Google Places/OpenStreetMap · Upstash Redis (opsiyonel hafıza)
>
> SEN4018 Dönem Projesi — Samet Soydan & Emre Sarkuş, Bahçeşehir Üniversitesi

---

## 🚀 Hızlı Başlangıç

```bash
# 1) Bağımlılıklar (Python 3.10+; 3.13/3.14 desteklenir)
pip install -r requirements.txt

# 2) .env dosyasını doldur (aşağıdaki tabloya bak)

# 3) Çalıştır
python app.py
# → http://127.0.0.1:7860
```

### Ortam değişkenleri (`.env`)

| Değişken | Zorunlu mu | Açıklama |
|---|---|---|
| `OPENAI_API_KEY` | ✅ Zorunlu | Tüm LLM çağrıları (öneri, sınıflandırma, çıkarım) |
| `OPENWEATHERMAP_API_KEY` | ✅ Zorunlu | Anlık hava durumu |
| `NOMINATIM_USER_AGENT` | ⚠️ Önerilir | OSM geocoding için kimlik (ör. `SkyWise/1.0 (mail@ornek.com)`) |
| `DEFAULT_CITY` | ⚪ Opsiyonel | Konum alınamazsa varsayılan şehir (varsayılan: Istanbul) |
| `GOOGLE_PLACES_API_KEY` | ⚪ Opsiyonel | Puanlı/fotoğraflı mekan + Google harita. Yoksa **OpenStreetMap** (Overpass + Leaflet) devreye girer |
| `UPSTASH_REDIS_REST_URL` | ⚪ Opsiyonel | Hafıza/oturum/favori kalıcılığı. Yoksa bellek-içi (oturum boyunca) çalışır |
| `UPSTASH_REDIS_REST_TOKEN` | ⚪ Opsiyonel | Redis kimliği |

> **Not:** Tahmin (saatlik/günlük), zaman şeridi, hafta planlayıcı ve UV verisi **Open-Meteo**
> üzerinden **ücretsiz, anahtar gerektirmeden** gelir.

---

## 🧪 Deneyebileceğin Her Şey

Aşağıdaki örnekleri arayüzdeki sohbet kutusuna yazarak (ya da ilgili butona tıklayarak)
deneyebilirsin. Çoğu özellik **kendiliğinden** (deterministik olarak) tetiklenir.

### 1) Sohbet & Aktivite Önerisi (çekirdek)

| Dene | Beklenen |
|---|---|
| *"Bugün ne yapabilirim?"* | Havaya uygun 3–4 somut öneri (gerçek mekan adı + neden + en iyi saat) |
| *"Müze öner"* / *"Yakında iyi kafeler"* | O kategoride gerçek mekanlar + harita |
| *"Bugün koşu için hava uygun mu?"* | Hava-öncelikli değerlendirme; uygunsa öneri, değilse iç-mekan alternatifi |
| *"Canım sıkıldı, bir şeyler öner"* | Belirsiz istekte hava-uygun öneriler |
| *"Beğenilerime göre öner"* | Kayıtlı tercihlerine ağırlık veren öneriler |
| Bir öneriden sonra *"başka?"*, *"peki orada?"* | Follow-up — aynı veriyi kullanır, tekrar aramaz |
| **Güvenlik:** fırtına/yağmur, 0°C altı, 38°C üstü, yüksek UV | Açık hava reddedilir; iç-mekan/gölge/serin saat önerilir |

### 2) Hava Durumu & Tahmin Paneli (sol panel)

| Dene | Beklenen |
|---|---|
| *"İstanbul'da hava nasıl?"* | Anlık hava kartı: sıcaklık, hissedilen, durum, şehir + 🌅 gün batımı ve ☀ UV çipleri |
| Herhangi bir öneri turu | **Zaman şeridi**: bugünün saatleri renkli (🟢 ideal / 🟡 UV / 🔵 yağış) + "🟢 En iyi saat: 14:00–17:00" |
| *"Yarın / hafta sonu hava nasıl?"* | Gün-gün tahmin metni (Open-Meteo) |
| Mekan önerisi | **Harita**: venue kartları (puan, mesafe, açık/kapalı, rota) + interaktif koyu harita |

### 3) Görsel & Tema

| Dene | Beklenen |
|---|---|
| Farklı havalı şehirler sor (güneşli/yağmurlu/karlı/gece) | **7 havaya duyarlı accent rengi** + uygun SVG ikon, yumuşak geçişle |
| Yağmurlu / karlı / gece bir şehir | **Ambient animasyon**: yağmur çizgileri / kar taneleri / yıldız parıltısı (işletim sisteminde "hareketi azalt" açıksa kapanır) |
| Mobil/dar pencere | Tek kolon responsive yerleşim |
| Üstteki **◀ / ☰** | Sol menüyü aç/kapat |

### 4) Kişiselleştirme & Hafıza

| Dene | Beklenen |
|---|---|
| İlk açılış (yeni kullanıcı) | **Onboarding**: "Hangi tür aktiviteleri seversin?" + 4 kategori kartı |
| Bir öneriye **👍 / 👎** (kart altındaki butonlar veya mesaj üstüne gelince) | Tercih kaydedilir; **kişiselleştirme rozeti** (Lv) yükselir |
| Birkaç tur sonra *"beğenilerime göre öner"* | Öğrenilen kategorilere göre öneri |
| **🔄 Tercihlerimi Sıfırla** | Öğrenilen tercihler + rozet sıfırlanır, onboarding döner *(favoriler silinmez)* |

### 5) Oturumlar (sol menü)

| Dene | Beklenen |
|---|---|
| **➕ Yeni Sohbet** | Sohbet + paneller temizlenir, konumun havasına döner |
| Geçmiş bir sohbete tıkla | Mesajlar + hava/harita anlık görüntüsü geri yüklenir |
| **✏️** yeniden adlandır / **🗑** sil | Oturum başlığı değişir / silinir (başlık ilk mesajdan LLM ile üretilir) |

### 6) Dil (TR ↔ EN)

| Dene | Beklenen |
|---|---|
| **🌐 EN / 🌐 TR** butonu | Tüm arayüz anında çevrilir; seçim tarayıcıda (localStorage) kalıcı olur |
| İngilizce yaz (*"What can I do today?"*) | Cevap otomatik İngilizce gelir (mesaj dilinden tespit) |

### 7) Konum

| Dene | Beklenen |
|---|---|
| Açılışta tarayıcı konum izni ver | Hava otomatik **senin konumuna** göre gelir |
| *"İzmir'deyim"* / *"Berlin'e taşındım"* | Konum güncellenir, panel anında o şehre döner |
| *"Londra'da bugün ne yaparım?"* | Mesajda geçen şehre göre öneri |

---

## ✨ Yeni Özellikler

Bu özellikler son geliştirme turunda eklendi:

### ☔ Yağmur Nowcast Alarmı
Önümüzdeki ~2 saatte yağış başlıyorsa hava kartının altında uyarı çıkar:
*"☔ Saat 16:00'de yağmur başlıyor — şemsiyeni al."* (Yağmur diniyorsa: *"🌤️ Yağmur 17:00 civarı diniyor."*)
**Dene:** yağışı yaklaşan bir şehir sor. *Önümüzdeki 2 saatte yağış yoksa uyarı çıkmaz.*

### 🌧️ Havaya Duyarlı Ambient Arka Plan
Tema yağmur/kar/gece olunca ekranda ince partiküller akar. Saf görsel; tıklamaları engellemez,
"hareketi azalt" tercihinde kapanır.

### 📅 Akıllı Hafta Planlayıcı (ısı haritası)
**Dene:** *"Bu hafta sonu piknik için en iyi gün hangisi?"* → zaman şeridinin altında
**gün × saat ideal-pencere ısı haritası** + *"🟢 En iyi pencere: Cumartesi 10:00–14:00"*.
Çok günlü (forecast) istek gerektirir; tek-gün sorularında çıkmaz.

### 📆 Takvime Ekle (.ics)
Bir aktivite önerisinden sonra **"📅 Takvime ekle"** butonu çıkar. Tıklayınca öneriden zamanlı
etkinlikler çıkarılıp indirilebilir bir **`.ics`** üretilir — Google / Apple / Outlook takvimlerinin
tümüne içe aktarılabilir.

### ⭐ Favori Mekanlar & Aktivite Günlüğü
Mekan önerisinden sonra haritanın altındaki **dropdown + "⭐ Kaydet"** ile mekanı favorile.
Sol menüde **"⭐ Favori Mekanlarım"** altında listelenir (🗺 rota linkiyle); altındaki seçiciden
bir favori seçip **✓** ile *"yaptım"* işaretlersin (üstü çizili) ya da **🗑** ile silersin.
Aynı tarayıcıda kalıcıdır; "Tercihlerimi Sıfırla" bunları silmez.

### ✈️ Seyahat Modu (çok şehir)
**Dene:** *"Hafta sonu Roma'ya gidiyorum, ne yapabilirim?"* → panel **hedef şehrin** havasını
gösterir, **"✈️ Seyahat havası"** kartında 🏠 konum vs 📍 hedef sıcaklık farkı çıkar, öneriler
hedefe özel olur. *(Karşılaştırma için bir "konum" gerekir — geolocation izni ver ya da önce
"İstanbul'dayım" de.)*

---

## ⌨️ Küçük Dokunuşlar

- **Streaming yanıt** + "yanıt hazırlanıyor" yazıyor göstergesi
- **Sonraki-prompt ipucu**: giriş kutusunda gri ipucu belirir; **Tab** ile otomatik doldurulur
- **Sıraya alma**: cevap üretilirken yeni mesaj yazarsan sıraya eklenir
- **Skeleton** yükleme animasyonu (hava paneli gelene kadar)
- Mesaj **kopyala** butonu

---

## 🧠 Nasıl Çalışır (özet)

1. **Dil tespiti** (mesajdan) + **intent sınıflandırma** (kural tabanlı, LLM'siz): yalnızca-hava,
   aktivite, follow-up, konum güncelleme.
2. **Hızlı yollar**: salt hava sorusu ve konum bildirimi ReAct'ı atlar (hız + maliyet).
3. **ReAct ajan** (LangGraph) 6 araçla: `current_weather`, `forecast`, `hourly_timing`,
   `comfort`, `venue_search`, `uv`.
4. **Supervisor** önerinin güvenlik/tutarlılık/kişiselleştirme kalitesini denetler.
5. **Hafıza** (arka planda): konuşmadan tercih çıkarımı, favori şehirler, özet — Redis'te anon_id ile.
6. **Önbellek**: hava/tahmin/mekan aynı gün için iki katmanlı (bellek + Redis) cache'lenir.

---

## 🗂️ Proje Yapısı

```
app.py            # Gradio arayüzü, olay zincirleri, panel/oturum/favori wiring
chat.py           # Sohbet katmanı: intent router, ReAct worker, araçlar, seyahat/konum tespiti
agent.py          # run_skywise() — LangGraph state machine giriş noktası (eval/grafik yolu)
i18n.py           # TR/EN arayüz metinleri (tek doğruluk kaynağı)
ui_theme.py       # Koyu glassmorphism tema, SVG ikonlar, panel/harita/şerit/ısı haritası render + CSS
core/
  graph.py        # plan → execute → recommend → evaluate döngüsü
  llms.py         # OpenAI istemcileri (react/evaluator/planner/itinerary)
  prompts.py      # Tüm sistem prompt'ları (TR/EN)
  state.py        # SkyWiseState tipleri
tools/
  weather.py      # OpenWeatherMap (anlık hava, konfor)
  forecast.py     # Open-Meteo (saatlik/günlük, zaman şeridi, hafta ısı haritası, yağmur nowcast)
  venue.py        # Google Places / OSM mekan arama + geocoding
  uv.py           # UV indeksi
  memory.py       # Anon hafıza, tercihler, kişiselleştirme seviyesi, favoriler
  sessions.py     # Oturum kaydet/yükle/sil
  cache.py        # İki katmanlı önbellek (bellek + Upstash Redis)
  calendar_ics.py # Öneriden .ics takvim üretimi
```

---

## 🧰 Teknoloji

Python · Gradio 5 · LangChain + LangGraph · OpenAI (gpt-4o-mini) · OpenWeatherMap · Open-Meteo ·
Google Places / OpenStreetMap (Nominatim + Overpass) · Folium/Leaflet · Plotly · Upstash Redis

---

## ⚠️ Notlar

- `OPENAI_API_KEY` ve `OPENWEATHERMAP_API_KEY` olmadan uygulama çalışmaz.
- Redis yoksa hafıza/oturum/favoriler **yalnızca o oturum boyunca** bellek-içi tutulur (kalıcı olmaz).
- Yağmur nowcast ve ambient animasyon **canlı hava koşullarına** bağlıdır; uygun koşul yoksa görünmez (hata değildir).
- `.env` ve API anahtarlarını **paylaşma / commit etme**.
