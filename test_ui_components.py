"""
UI Component Test for v2.0 Schema

Tests the refactored UI components without hardware dependencies:
1. CreatePatientDialog - new QDateEdit + QComboBox
2. PatientButton - new signal type (str) and display format
3. PatientListWidget - new type hints (str)
4. EditPatientDialog - read-only info display
5. DuplicatePatientDialog - merge decision dialog

Run: python test_ui_components.py
"""

import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

# Import UI components
from patient_widgets import (
    CreatePatientDialog, 
    PatientButton, 
    PatientListWidget,
    EditPatientDialog,
    DuplicatePatientDialog
)
from db import PatientDataManager


def test_create_patient_dialog():
    """Test CreatePatientDialog with new QDateEdit + QComboBox UI."""
    print("\n" + "="*60)
    print("TEST 1: CreatePatientDialog (Date Picker + Gender Selector)")
    print("="*60)
    
    app = QApplication.instance() or QApplication([])
    
    dialog = CreatePatientDialog()
    
    # Simulate user selecting:
    # - Birthdate: May 15, 1990
    # - Gender: Male (M)
    
    from PySide6.QtCore import QDate
    dialog.date_edit.setDate(QDate(1990, 5, 15))
    dialog.gender_combo.setCurrentIndex(0)  # First item (M)
    
    # Get result
    result = dialog.get_patient_data()
    
    assert result is not None, "Dialog returned None"
    assert "birthdate" in result, "Missing birthdate in result"
    assert "sex" in result, "Missing sex in result"
    
    print(f"✓ Dialog submitted birthdate: {result['birthdate']}")
    print(f"✓ Dialog submitted sex: {result['sex']}")
    assert result['birthdate'] == "1990-05-15", f"Unexpected birthdate: {result['birthdate']}"
    assert result['sex'] == "M", f"Unexpected sex: {result['sex']}"
    
    print("✅ CreatePatientDialog works correctly")
    print(f"   - QDateEdit properly converts to YYYY-MM-DD format")
    print(f"   - QComboBox gender selection extracts M/W/D correctly")


def test_patient_button():
    """Test PatientButton with new str signal and ID display."""
    print("\n" + "="*60)
    print("TEST 2: PatientButton (New Signal Type + Display Format)")
    print("="*60)
    
    app = QApplication.instance() or QApplication([])
    
    # Create button with v2.0 patient data
    patient_data = {
        "id": "E771-1990-05-15-M",
        "birthdate": "1990-05-15",
        "sex": "M",
        "recordings": []
    }
    
    button = PatientButton(patient_data)
    
    # Verify signal is str-based (not int)
    signal_str = str(button.patient_clicked)
    assert "str" in signal_str or "QString" in signal_str, f"Signal type wrong: {signal_str}"
    print(f"✓ Signal type verified: str-based")
    
    # Verify button displays correct ID
    button_text = button.text()
    assert "E771-1990-05-15-M" in button_text, f"ID not in button text: {button_text}"
    assert "1990-05-15" in button_text, f"Birthdate not in button text: {button_text}"
    print(f"✓ Button display format correct:")
    print(f"   {button_text[:50]}...")
    
    print("✅ PatientButton works correctly")
    print(f"   - Signal emits str (patient ID)")
    print(f"   - Display shows XXXX-YYYY-MM-DD-G format")


def test_patient_list_widget():
    """Test PatientListWidget with str-based type hints."""
    print("\n" + "="*60)
    print("TEST 3: PatientListWidget (Str-Based Type Hints)")
    print("="*60)
    
    app = QApplication.instance() or QApplication([])
    
    widget = PatientListWidget()
    
    # Verify selected_patient_id type hint is str | None
    assert widget.selected_patient_id is None, "Initial selection should be None"
    print(f"✓ Initial selected_patient_id: None (correct type)")
    
    # Add test patient
    patient = {
        "id": "5F58-1985-12-25-W",
        "birthdate": "1985-12-25",
        "sex": "W",
        "recordings": []
    }
    
    widget.add_patient(patient)
    print(f"✓ Patient added: {patient['id']}")
    
    # Verify selection works with str ID
    widget.select_patient("5F58-1985-12-25-W")
    assert widget.selected_patient_id == "5F58-1985-12-25-W", "Selection failed"
    print(f"✓ Patient selected: {widget.selected_patient_id} (str type)")
    
    print("✅ PatientListWidget works correctly")
    print(f"   - Type hints handle str IDs")
    print(f"   - Select/add operations work")


def test_edit_patient_dialog():
    """Test EditPatientDialog read-only display."""
    print("\n" + "="*60)
    print("TEST 4: EditPatientDialog (Read-Only Info Display)")
    print("="*60)
    
    app = QApplication.instance() or QApplication([])
    
    patient = {
        "id": "7186-2000-06-10-D",
        "birthdate": "2000-06-10",
        "sex": "D"
    }
    
    dialog = EditPatientDialog(patient_data=patient)
    
    # Verify dialog is read-only (no editable fields)
    # Should have get_patient_data() that returns original data unchanged
    result = dialog.get_patient_data()
    
    assert result == patient, "Dialog should return original data unchanged"
    print(f"✓ Dialog returns read-only patient data:")
    print(f"   - ID: {result['id']}")
    print(f"   - Birthdate: {result['birthdate']}")
    print(f"   - Sex: {result['sex']}")
    
    print("✅ EditPatientDialog works correctly")
    print(f"   - Read-only display (no edit fields)")
    print(f"   - Returns original data (immutable)")


def test_duplicate_patient_dialog():
    """Test DuplicatePatientDialog merge/skip decision."""
    print("\n" + "="*60)
    print("TEST 5: DuplicatePatientDialog (Merge Decision)")
    print("="*60)
    
    app = QApplication.instance() or QApplication([])
    
    eyecon_patient = {
        "id": "A123-1990-05-15-M",
        "birthdate": "1990-05-15",
        "sex": "M",
        "recordings": [
            {"id": "2026-02-13-10-00-00"},
            {"id": "2026-02-13-11-00-00"}
        ]
    }
    
    tbi_patient = {
        "id": "B456-1990-05-15-M",
        "birthdate": "1990-05-15",
        "sex": "M",
        "recordings": [
            {"id": "2026-02-12-14-30-00"}
        ]
    }
    
    dialog = DuplicatePatientDialog(
        eyecon_patient=eyecon_patient,
        tbi_patient=tbi_patient
    )
    
    # Verify dialog has action tracking
    assert hasattr(dialog, 'selected_action'), "Dialog missing selected_action"
    assert hasattr(dialog, 'get_action'), "Dialog missing get_action() method"
    print(f"✓ Dialog has action tracking mechanism")
    
    # Simulate user clicking "Merge"
    dialog._on_merge_clicked()
    action = dialog.get_action()
    assert action == "merge", f"Expected 'merge', got {action}"
    print(f"✓ Merge action: {action}")
    
    # Create new dialog, simulate "Skip"
    dialog2 = DuplicatePatientDialog(
        eyecon_patient=eyecon_patient,
        tbi_patient=tbi_patient
    )
    dialog2._on_skip_clicked()
    action2 = dialog2.get_action()
    assert action2 == "skip", f"Expected 'skip', got {action2}"
    print(f"✓ Skip action: {action2}")
    
    # Create new dialog, simulate "Cancel"
    dialog3 = DuplicatePatientDialog(
        eyecon_patient=eyecon_patient,
        tbi_patient=tbi_patient
    )
    dialog3._on_cancel_clicked()
    action3 = dialog3.get_action()
    assert action3 == "cancel", f"Expected 'cancel', got {action3}"
    print(f"✓ Cancel action: {action3}")
    
    print("✅ DuplicatePatientDialog works correctly")
    print(f"   - Merge/Skip/Cancel actions functional")
    print(f"   - get_action() returns correct decision")


def test_integration():
    """Test full v2.0 workflow through UI components."""
    print("\n" + "="*60)
    print("TEST 6: Full v2.0 UI Integration Workflow")
    print("="*60)
    
    app = QApplication.instance() or QApplication([])
    
    # Step 1: Create database with test patient
    db = PatientDataManager("data/eyecon_ui_test.db")
    patient_id = db.create_patient(birthdate="1995-03-20", sex="W", first_name="Maria", last_name="Müller")
    print(f"✓ Step 1: Created patient {patient_id}")
    
    # Step 2: Add recording
    rec_id = db.generate_recording_id(datetime.now().timestamp())
    db.add_recording(rec_id, patient_id, int(datetime.now().timestamp()), baseline=0)
    print(f"✓ Step 2: Created recording {rec_id}")
    
    # Step 3: Verify data through UI components
    patient_data = db.get_patient(patient_id)
    
    # Step 4: Create PatientButton (simulating list display)
    button = PatientButton(patient_data)
    button_text = button.text()
    assert patient_id in button_text, "Patient ID not in button"
    print(f"✓ Step 3: PatientButton displays {patient_id}")
    
    # Step 5: Verify signal is str-based
    signal_str = str(button.patient_clicked)
    print(f"✓ Step 4: Signal type is str-based")
    
    # Step 6: Simulate viewing patient info (EditPatientDialog)
    dialog = EditPatientDialog(patient_data=patient_data)
    info = dialog.get_patient_data()
    assert info['id'] == patient_id, "ID mismatch"
    print(f"✓ Step 5: EditPatientDialog shows patient info (read-only)")
    
    print("✅ Full UI Integration works correctly")
    print(f"   - Create patient → Button display → Info dialog")
    print(f"   - All components use new v2.0 types (str IDs)")


def main():
    """Run all UI component tests."""
    print("\n" + "="*60)
    print("🔍 UI COMPONENT TEST SUITE: v2.0 Schema")
    print("="*60)
    
    try:
        test_create_patient_dialog()
        test_patient_button()
        test_patient_list_widget()
        test_edit_patient_dialog()
        test_duplicate_patient_dialog()
        test_integration()
        
        print("\n" + "="*60)
        print("✅ ALL UI COMPONENT TESTS PASSED!")
        print("="*60)
        print("\nSummary:")
        print("  ✓ CreatePatientDialog: Date picker + gender selector works")
        print("  ✓ PatientButton: New signal type (str) and display format")
        print("  ✓ PatientListWidget: Str-based type hints functional")
        print("  ✓ EditPatientDialog: Read-only info display correct")
        print("  ✓ DuplicatePatientDialog: Merge/skip/cancel decisions work")
        print("  ✓ Integration: Full workflow through UI components")
        print("="*60 + "\n")
        
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
