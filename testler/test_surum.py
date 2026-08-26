"""İstemci/sunucu sürüm tutarlılığı — AĞ GEREKTİRMEZ.

SESSİZ ARIZA: telefon müfredatı ve sözlüğü bir kez indirip saklıyor.
Yeniden indirmesinin tek tetiği sürüm numarası:

    bool get mufredatVar => moduller.isNotEmpty && mufredatBankaSurum >= mufredatSurum;

Sunucuda içerik değişip sürüm artmazsa telefon eski metni göstermeye
devam eder. Sunucuda sürüm artıp Dart tarafındaki sabit artmazsa da aynı
şey olur: kayıtlı kopya hâlâ "yeterince yeni" sayılır ve istek hiç
atılmaz. İkisi de sessizdir — kimse hata görmez, sadece yeni ders
telefonda yoktur.

Bu test o iki sayıyı birbirine bağlar.

Çalıştır:  .venv/bin/python -m pytest testler/ -q
"""
import re
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parent.parent
DART_EGITMEN = KOK / "mobil" / "lib" / "servis" / "egitmen.dart"


def _dart_sabiti(dosya: Path, ad: str) -> int:
    m = re.search(rf"static const {ad}\s*=\s*(\d+)\s*;", dosya.read_text("utf-8"))
    assert m, f"{dosya.name} içinde '{ad}' sabiti bulunamadı"
    return int(m.group(1))


@pytest.fixture
def istemci(monkeypatch):
    """Anahtarsız bir sunucu örneği.

    `_ANAHTAR` modül yüklenirken .env'den okunuyor. Ortam değişkenini
    silmek yetmez — .env'i yükleyen `ortam` modülü zaten import edilmiş
    olabilir ve os.environ'a anahtarı çoktan yazmıştır. Bu yüzden modül
    değişkeni doğrudan boşaltılır: test, geliştirme makinesindeki .env'e
    bağlı olmamalı."""
    from fastapi.testclient import TestClient
    import api.main as m
    monkeypatch.setattr(m, "_ANAHTAR", "")
    # Açılışta 100 hisse indirmesin.
    monkeypatch.setattr(m.onbellek, "arka_planda_isit", lambda *a, **k: None)
    monkeypatch.setattr(m.onbellek, "periyodik", lambda *a, **k: None)
    with TestClient(m.app) as c:
        yield c


def _api_surum(istemci, yol: str) -> int:
    r = istemci.get(yol)
    assert r.status_code == 200, f"{yol} -> {r.status_code}"
    return int(r.json()["surum"])


def test_mufredat_surumu_istemciyle_ayni(istemci):
    sunucu = _api_surum(istemci, "/egitmen/mufredat")
    istemci = _dart_sabiti(DART_EGITMEN, "mufredatSurum")
    assert sunucu == istemci, (
        f"sunucu müfredat sürümü {sunucu}, telefondaki sabit {istemci}. "
        f"İkisi eşit olmazsa telefon ya eski müfredatı gösterir ya da "
        f"her açılışta gereksiz yere yeniden indirir.")


def test_soru_bankasi_surumu_istemciyle_ayni(istemci):
    sunucu = _api_surum(istemci, "/egitmen/sorular")
    istemci = _dart_sabiti(DART_EGITMEN, "surum")
    assert sunucu == istemci, (
        f"sunucu soru bankası sürümü {sunucu}, telefondaki sabit {istemci}.")


def test_sozluk_surumu_var(istemci):
    """Sözlük de önbelleğe alınıyor; sürümsüz bir yanıt onbelleği
    tazelenemez hale getirir."""
    assert _api_surum(istemci, "/sozluk") >= 1
