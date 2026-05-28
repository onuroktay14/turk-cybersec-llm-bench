# SOC Alert Triage — cybersec-llm-bench v1 (TR)

Sen bir Tier-2 SOC analistisin. Aşağıdaki SIEM alert'ini incele ve **kesinlikle aşağıdaki format şablonuna uyarak** kararını ver.

Türkçe açıklama yaz, teknik terimleri (process, hash, MITRE ATT&CK technique, registry, IOC, vb.) İngilizce bırak.

## Alert
```json
{alert_json}
```

## Çıktı Formatı — Bu Markdown başlıklarını AYNEN kullan

### Verdict
Tek satır. Sadece şunlardan biri: `TP` | `FP` | `BENIGN` | `SUSPICIOUS`

### Confidence
Tek satır. Sadece şunlardan biri: `LOW` | `MEDIUM` | `HIGH`

### Reasoning
2–4 cümle. Hangi göstergeler (process tree, command line, hedef proses, access mask, parent–child ilişkisi, network destination vb.) kararı destekliyor? Genel cümleler yazma — somut alanlara referans ver.

### MITRE ATT&CK
İlgili teknikleri `T1234` veya `T1234.001` formatında virgülle ayrılmış olarak ver. Birden fazla varsa hepsini yaz. İlgisizse `N/A` yaz.

### Recommended Actions
1–3 maddelik, somut ve uygulanabilir aksiyonlar. Genel tavsiyeden kaçın — host izolasyonu, EDR auto-block, threat hunt query, IR escalation gibi net adımlar belirt.

### IOCs
JSON object olarak: `{"ips": [...], "hashes": [...], "domains": [...], "users": [...]}`. Boş alanlar için `[]` kullan, alan yoksa anahtarı bırak.

---

**Önemli kurallar:**
- Format şablonundan sapma. Her başlık aynen yukarıdaki gibi yazılmalı (`### Verdict`, `### Confidence`, vb.).
- Reasoning bölümünde hallucination yapma — sadece alert payload'ında verilen alanlardan referans ver.
- Bilmediğin şey için "bilmiyorum" yaz, uydurma.
