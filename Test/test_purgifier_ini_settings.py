from ReportFileMover import ReportFileMover


def test_file_mover_instantiation():
    mv_mover = ReportFileMover('MicroVUFileMover')
    assert mv_mover._root_path == 'S:\\Micro-Vu'
    assert mv_mover._pdf_archive_dir == 'S:\\Micro-Vu\\Archives'
    assert mv_mover._pdf_file_days_to_keep == 30

    cmm_mover = ReportFileMover('CMMFileMover')
    assert cmm_mover._root_path == 'S:\\CMM'
    assert cmm_mover._pdf_archive_dir == 'S:\\CMM\\Archives'
    assert cmm_mover._pdf_file_days_to_keep == 90

    sp_mover = ReportFileMover('SmartProfileFileMover')
    assert sp_mover._root_path == 'S:\\Smart Profile'
    assert sp_mover._pdf_archive_dir == 'S:\\Smart Profile\\Archives'
    assert sp_mover._pdf_file_days_to_keep == 60
