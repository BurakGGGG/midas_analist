"""Fiyat verisi önbelleği.

Bu dosyanın konusu VERİNİN KENDİSİ değil, ne zaman yeniden indirildiği.
Yanlış tazelik kararı iki yönde de pahalı: erken indirmek her çağrıyı
saniyelere çıkarıyor, geç indirmek geçmişi sığ bırakıp backtest'i
sessizce yanlış hesaplatıyor.
"""
from cekirdek import veri




# ═══════════════════════════════════ derinlik kaydı (yeni halka arzlar)
#
# Geçmişi 700 gün olan bir hisse 1300 gün istendiğinde derinlik koşulunu
# ASLA sağlayamaz; önbellek daima bayat sayılır ve her çağrı yeniden
# indirir. 100 hisselik bir tarama bu yüzden 164 saniye sürüyordu.

def test_kisa_gecmisli_hisse_surekli_yeniden_INDIRILMEZ(tmp_path, monkeypatch):
    import json
    import pandas as pd
    from datetime import datetime, timedelta

    monkeypatch.setattr(veri, "ONBELLEK", tmp_path)
    monkeypatch.setattr(veri, "DERINLIK_KAYDI", tmp_path / "derinlik.json")

    # 700 günlük geçmişi olan bir hisse
    idx = pd.date_range(end=datetime.now(), periods=700, freq="D")
    df = pd.DataFrame({"Open": 1.0, "High": 1.0, "Low": 1.0,
                       "Close": 1.0, "Volume": 1.0}, index=idx)
    yol = tmp_path / "YENI_1d.pkl"
    df.to_pickle(yol)
    gerekli = datetime.now() - timedelta(days=1300)

    # Kayıt YOKKEN: derinlik yetmiyor, bayat sayılmalı
    assert veri._taze_mi(yol, 12.0, gerekli, sembol="YENI", gun=1300) is False

    # 1300 gün derinliğinde zaten sorulmuşsa: gelen veri hissenin tamamı
    (tmp_path / "derinlik.json").write_text(json.dumps({"YENI": 1300}),
                                            encoding="utf-8")
    assert veri._taze_mi(yol, 12.0, gerekli, sembol="YENI", gun=1300) is True


def test_daha_derin_istek_yeniden_indirtir(tmp_path, monkeypatch):
    """Kayıt 700'se ve 1300 isteniyorsa yine indirilmeli — belki
    yfinance bu sefer daha fazlasını verir."""
    import json
    import pandas as pd
    from datetime import datetime, timedelta

    monkeypatch.setattr(veri, "ONBELLEK", tmp_path)
    monkeypatch.setattr(veri, "DERINLIK_KAYDI", tmp_path / "derinlik.json")
    idx = pd.date_range(end=datetime.now(), periods=700, freq="D")
    pd.DataFrame({"Open": 1.0, "High": 1.0, "Low": 1.0, "Close": 1.0,
                  "Volume": 1.0}, index=idx).to_pickle(tmp_path / "YENI_1d.pkl")
    (tmp_path / "derinlik.json").write_text(json.dumps({"YENI": 700}),
                                            encoding="utf-8")
    gerekli = datetime.now() - timedelta(days=1300)
    assert veri._taze_mi(tmp_path / "YENI_1d.pkl", 12.0, gerekli,
                         sembol="YENI", gun=1300) is False


def test_derinlik_kaydi_geriye_gitmez(tmp_path, monkeypatch):
    monkeypatch.setattr(veri, "DERINLIK_KAYDI", tmp_path / "derinlik.json")
    veri._derinlik_yaz("X", 1300)
    veri._derinlik_yaz("X", 400)          # daha sığ istek kaydı bozmamalı
    assert veri._derinlikler()["X"] == 1300


def test_derinlik_kaydi_bozuksa_cokmez(tmp_path, monkeypatch):
    yol = tmp_path / "derinlik.json"
    yol.write_text("bozuk json", encoding="utf-8")
    monkeypatch.setattr(veri, "DERINLIK_KAYDI", yol)
    assert veri._derinlikler() == {}
