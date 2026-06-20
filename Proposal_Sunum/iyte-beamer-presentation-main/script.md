# VoxMed - 3 Dakikalık Sunum Konuşma Metni (Turkish Speech Script)

*Bu konuşma metni, slaytlarla senkronize ve yaklaşık 3 dakikalık (orta-sakin hızda okunacak şekilde, ~420 kelime) hazırlanmıştır.*

---

### Slayt 1: Giriş (Title Slide)
**Süre: ~25 saniye**

> "Merhaba hocalarım ve arkadaşlarım, ben Barış. Bugün sizlere EE471 dersi kapsamında geliştireceğimiz final projemiz **VoxMed**'i sunacağım. Projemizin amacı, görme engelli ve yaşlı bireylerin ilaç ve gıda tüketim güvenliğini artırmak için mobil ve yapay zeka teknolojilerini birleştiren sesli bir asistan geliştirmektir. Dersi veren Cihan Göksu hocamızın rehberliğinde yürüteceğimiz bu çalışmanın detaylarına geçelim."

---

### Slayt 2: Problem ve Motivasyon (1_problem.tex)
**Süre: ~45 saniye**

> "İlk olarak problemimizden bahsetmek istiyorum. Günümüzde gıda paketlerinin arkasındaki içindekiler kısmı ve ilaç kutularının üzerindeki prospektüs bilgileri son derece küçük yazı tipleriyle yazılmaktadır. Bu durum, görme engelli veya yaşlı bireyler için ciddi bir erişilebilirlik bariyeri oluşturuyor. 
> 
> Buna ek olarak, seyahat eden veya yabancı dil bilmeyen bireyler için ambalajlardaki dil bariyeri de ciddi bir alerjen riski barındırmaktadır. Yanlışlıkla tüketilen bir alerjen madde, örneğin yer fıstığı veya gluten, hayati tehlike oluşturabilen anafilaktik şoklara yol açabiliyor. Benzer şekilde, yabancı ilaçların etkin maddelerinin yanlış okunması da ölümcül sonuçlar doğurabilir. VoxMed, bu bireylerin kimseye ihtiyaç duymadan, hem kendi ülkelerinde hem de yurt dışında güvenle alışveriş yapabilmelerini ve ilaç kullanabilmelerini hedefliyor."

---

### Slayt 3: Önerilen Çözüm: VoxMed (2_solution.tex)
**Süre: ~45 saniye**

> "VoxMed, tamamen sesle kontrol edilebilen, erişilebilirlik odaklı bir mobil uygulamadır. Kullanıcı, paketin fotoğrafını çektiğinde sistem arkadaki tüm yazıları OCR teknolojisiyle dijital metne dönüştürür. Sistemimiz, çok dilli destek yapısı sayesinde farklı dillerdeki içerikleri otomatik olarak algılar ve Türkçe'ye çevirerek analiz edebilir.
> 
> Ardından, bu verileri kullanıcının AWS bulut üzerinde saklanan alerji ve sağlık profiliyle karşılaştırır. Yerel yapay zeka modelimiz SmolLM2, metni saniyeler içinde analiz ederek içerikte bir tehlike olup olmadığını belirler. Kullanıcıya hem ekranda büyük görsel uyarılarla hem de telefonun kendi ses motorunu kullanarak Türkçe sesli geri bildirimle uyarısını yapar. Ayrıca kullanıcı, sesli olarak 'İçinde ne kadar şeker var?' gibi takip soruları sorup anında yanıt alabilir."

---

### Slayt 4: Sistem Mimarisi (3_architecture.tex)
**Süre: ~35 saniye**

> "Sistemimiz EE471 dersinde öğrendiğimiz melez mimariyi (Edge-Cloud Hybrid) temel alıyor. 
> 
> Donanım kısıtlamalarını aşmak için, ağır yapay zeka modelleri olan Whisper, SmolLM2 ve OCR'ı kullanıcının yerel bilgisayarındaki ekran kartını kullanarak Flask API üzerinde çalıştıracağız. 
> 
> Kullanıcı profilleri, tarama logları ve çekilen fotoğraflar ise AWS EC2 ve AWS S3 bulut sunucumuzda barındırılacak. Dağıtım sürecini tamamen Dockerize edip, yazacağımız GitHub Actions CI/CD hattıyla otomatik hale getireceğiz. Böylece her kod güncellemesi doğrudan AWS sunucumuza otomatik olarak deploy edilecek."

---

### Slayt 5: Proje Takvimi ve Canlı Demo Senaryosu (4_timeline.tex & 5_impact.tex)
**Süre: ~30 saniye**

> "Proje takvimimizi 3 haftalık aşamalara böldük. İlk hafta AWS ve Django veritabanı altyapısını kuracağız. İkinci hafta yerel yapay zeka modellerinin prompt mühendisliğini ve OCR entegrasyonunu tamamlayacağız. Son hafta ise Flutter uygulamasını geliştirip, ses motorunu bağlayıp CI/CD süreçlerini tamamlayarak teslim edeceğiz.
> 
> Final sunumunda sınıfta gerçekleştireceğimiz canlı demoda, fıstık alerjisi olan Barış kullanıcısının elindeki çikolatayı taratmasını, telefon ekranının kırmızıya dönüp sesli olarak 'Dikkat yer fıstığı tespit edildi' demesini ve Barış'ın sesli takip sorularına uygulamanın cevap vermesini hep birlikte test edeceğiz. Dinlediğiniz için teşekkür ederim, sorularınızı yanıtlamaktan memnuniyet duyarım."
