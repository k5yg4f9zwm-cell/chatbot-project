import pytest
from chatbot import service


@pytest.fixture()
def db():
    d = service.connect()
    service.add_admin(d, "admin", "secret123")
    service.add_faq(d, "Құжаттар тізімі қандай?", "Төлқұжат және аттестат қажет.", "Қабылдау")
    return d


def test_add_admin_ok(db):
    service.add_admin(db, "manager", "pass123")
    assert service.verify_admin(db, "manager", "pass123") is True


def test_add_admin_duplicate(db):
    with pytest.raises(service.ChatbotError):
        service.add_admin(db, "admin", "otherpass")


def test_verify_admin_fail(db):
    assert service.verify_admin(db, "admin", "wrongpass") is False


def test_add_faq_ok(db):
    fid = service.add_faq(db, "Грант бар ма?", "Иә, гранттар бар.", "Грант")
    assert fid > 0


def test_add_faq_empty(db):
    with pytest.raises(service.ChatbotError):
        service.add_faq(db, "", "", "")


def test_update_faq_ok(db):
    service.update_faq(db, 1, "Жаңа сұрақ?", "Жаңа жауап.", "Жаңа санат")
    faqs = service.get_all_faqs(db)
    assert faqs[0]["question"] == "Жаңа сұрақ?"


def test_delete_faq_ok(db):
    service.delete_faq(db, 1)
    assert len(service.get_all_faqs(db)) == 0


def test_delete_faq_not_found(db):
    with pytest.raises(service.ChatbotError):
        service.delete_faq(db, 999)


def test_search_faq_found(db):
    res = service.search_faq(db, "құжат")
    assert len(res) >= 1
    logs = service.get_logs(db)
    assert len(logs) >= 1


def test_search_faq_empty_query(db):
    with pytest.raises(service.ChatbotError):
        service.search_faq(db, "   ")


def test_backup_and_restore(tmp_path):
    db_path = str(tmp_path / "test.sqlite")
    backup_path = str(tmp_path / "test_bk.sqlite")

    d = service.connect(db_path)
    service.add_faq(d, "Тест", "Жауап", "Санат")
    d.close()

    assert service.backup_database(db_path, backup_path) is True
    assert service.restore_database(backup_path, db_path) is True