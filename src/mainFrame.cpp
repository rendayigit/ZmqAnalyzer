#include "mainFrame.hpp"

#include "subscriberPanel.hpp"

#include <wx/defs.h>
#include <wx/notebook.h>
#include <wx/textctrl.h>

constexpr int MAIN_WINDOW_SIZE_X = 800;
constexpr int MAIN_WINDOW_SIZE_Y = 600;

// Main frame constructor
MainFrame::MainFrame()
    : wxFrame(nullptr, wxID_ANY, "Template Wx Cpp GUI Application", wxDefaultPosition,
              wxSize(MAIN_WINDOW_SIZE_X, MAIN_WINDOW_SIZE_Y)) {

  // Create menu bar
  auto *menuFile = new wxMenu;
  auto *helloMenuItem = menuFile->Append(wxID_ANY, "&Hello...\tCtrl-H", "Show hello dialog");
  menuFile->AppendSeparator();
  menuFile->Append(wxID_EXIT);

  auto *menuHelp = new wxMenu;
  menuHelp->Append(wxID_ABOUT);

  auto *menuBar = new wxMenuBar;
  menuBar->Append(menuFile, "&File");
  menuBar->Append(menuHelp, "&Help");

  SetMenuBar(menuBar);

  // Create status bar
  CreateStatusBar();
  SetStatusText("Welcome to wxWidgets!");

  // Create main panel
  panel = new wxPanel(this, wxID_ANY);

  // Create notebook with two tabs
  notebook = new wxNotebook(panel, wxID_ANY);

  // Create tab panels
  subscriber = new SubscriberPanel(notebook);

  // Add tabs to notebook
  notebook->AddPage(subscriber, "Subscriber");

  // Layout notebook in main panel
  sizer = new wxBoxSizer(wxVERTICAL);
  sizer->Add(notebook, 1, wxALL | wxEXPAND, wxSizerFlags::GetDefaultBorder());
  panel->SetSizer(sizer);

  Bind(wxEVT_MENU, &MainFrame::onExit, this, wxID_EXIT);
  Bind(wxEVT_MENU, &MainFrame::onAbout, this, wxID_ABOUT);
  Bind(wxEVT_MENU, &MainFrame::onHello, this, helloMenuItem->GetId());
}

void MainFrame::onExit(wxCommandEvent &event) {
  Close(true);
  event.Skip();
}

// TODO: Implement
void MainFrame::onAbout(wxCommandEvent &event) { // NOLINT(readability-convert-member-functions-to-static)
  wxMessageBox("ZMQ Analyzer", "About", wxOK | wxICON_INFORMATION); // NOLINT(hicpp-signed-bitwise)
  event.Skip();
}

// TODO: Implement
void MainFrame::onHello(wxCommandEvent &event) { // NOLINT(readability-convert-member-functions-to-static)
  wxLogMessage("Hello");
  event.Skip();
}
