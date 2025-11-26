#pragma once

#include <wx/listctrl.h>
#include <wx/wx.h>

class PublisherPanel : public wxPanel {
public:
  explicit PublisherPanel(wxWindow *parent);

private:
  void onPublishMessage(wxCommandEvent &event);

  void onRecentMessageSelected(wxListEvent &event);
  void onRecentMessageRightClick(wxListEvent &event);

  void onUseContextMenu(wxCommandEvent &event);
  void onCopyContextMenu(wxCommandEvent &event);
  void onDeleteContextMenu(wxCommandEvent &event);

  wxBoxSizer *mainSzr;
  wxBoxSizer *topSzr;
  wxBoxSizer *centerSzr;
  wxBoxSizer *messageSzr;
  wxBoxSizer *controlsSzr;

  wxTextCtrl *portTxtCtrl;
  wxTextCtrl *topicTxtCtrl;
  wxTextCtrl *messageTxtCtrl;

  wxButton *publishBtn;

  wxListCtrl *recentPublishedMsgsListCtrl;
};
