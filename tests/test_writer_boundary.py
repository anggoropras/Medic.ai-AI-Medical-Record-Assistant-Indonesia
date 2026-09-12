from agents.writer import WriterBoundary


def test_writer_requires_confirmation():
    boundary = WriterBoundary()
    record = {"status_data": "Lengkap", "Patient Name": "Pasien Uji"}
    assert boundary.can_write(record, False) is False
    assert boundary.can_write(record, True) is True


def test_writer_rejects_incomplete_record():
    boundary = WriterBoundary()
    record = {"status_data": "Data Tidak Lengkap"}
    assert boundary.can_write(record, True) is False
