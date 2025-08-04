#include "helloPanel.hpp"

#include <wx/textctrl.h>

// Main frame constructor
HelloPanel::HelloPanel(wxWindow *parent) : wxPanel(parent, wxID_ANY), sizer(new wxBoxSizer(wxVERTICAL)) {

  // Create controls
  label = new wxStaticText(this, wxID_ANY, HELLO_MESSAGE);
  sizer->Add(label, 0, wxALL | wxCENTER, wxSizerFlags::GetDefaultBorder());
  textCtrl = new wxTextCtrl(this, wxID_ANY, HELLO_MESSAGE, wxDefaultPosition, wxDefaultSize, wxTE_MULTILINE);
  sizer->Add(textCtrl, 1, wxALL | wxEXPAND, wxSizerFlags::GetDefaultBorder());
  button = new wxButton(this, wxID_ANY, "Say Hello");
  sizer->Add(button, 0, wxALL | wxCENTER, wxSizerFlags::GetDefaultBorder());

  SetSizer(sizer);

  Bind(wxEVT_BUTTON, &HelloPanel::onHello, this, button->GetId());
  textCtrl->Bind(wxEVT_CHAR, &HelloPanel::updateLabelText, this);
}

void HelloPanel::updateLabelText(wxKeyEvent &event) {
  label->SetLabel(textCtrl->GetValue());
  event.Skip();
}

void HelloPanel::onHello(wxCommandEvent &event) { // NOLINT(readability-convert-member-functions-to-static)
  wxLogMessage(HELLO_MESSAGE);
  event.Skip();
}