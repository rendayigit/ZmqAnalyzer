#include "mainFrame.hpp"

#include "requester/requesterPanel.hpp"
#include "subscriber/subscriberPanel.hpp"
#include "wxConstants.hpp"

#include <wx/defs.h>
#include <wx/notebook.h>
#include <wx/textctrl.h>

constexpr int MAIN_WINDOW_SIZE_X = 1000;
constexpr int MAIN_WINDOW_SIZE_Y = 600;

// Main frame constructor
MainFrame::MainFrame()
    : wxFrame(nullptr, wxID_ANY, "ZeroMQ Analyzer", wxDefaultPosition, wxSize(MAIN_WINDOW_SIZE_X, MAIN_WINDOW_SIZE_Y)),
      sizer(new wxBoxSizer(wxVERTICAL)) {

  // Create menu bar
  auto *menuFile = new wxMenu;
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
  SetStatusText("Welcome to ZeroMQ Analyzer!");

  // Create main panel
  panel = new wxPanel(this, wxID_ANY);

  // Create notebook with two tabs
  notebook = new wxNotebook(panel, wxID_ANY);

  // Create tab panels
  subscriber = new SubscriberPanel(notebook); // NOLINT(cppcoreguidelines-prefer-member-initializer)

  // Create requester panel
  requester = new RequesterPanel(notebook); // NOLINT(cppcoreguidelines-prefer-member-initializer)

  // Add tabs to notebook
  notebook->AddPage(subscriber, "Subscriber");
  notebook->AddPage(requester, "Requester");

  // Layout notebook in main panel
  sizer->Add(notebook, 1, WX_EXPAND, wxSizerFlags::GetDefaultBorder());
  panel->SetSizer(sizer);

  Bind(wxEVT_MENU, &MainFrame::onExit, this, wxID_EXIT);
  Bind(wxEVT_MENU, &MainFrame::onAbout, this, wxID_ABOUT);
}

void MainFrame::onExit(wxCommandEvent &event) {
  Close(true);
  event.Skip();
}

void MainFrame::onAbout(wxCommandEvent &event) { // NOLINT(readability-convert-member-functions-to-static)
  wxMessageBox("This application allows you to transmit and receive messages using ZeroMQ.\nPlease refer to "
               "https://github.com/rendayigit/ZmqAnalyzer for more information.",
               "About ZeroMQ Analyzer", wxOK | wxICON_INFORMATION); // NOLINT(hicpp-signed-bitwise)
  event.Skip();
}
