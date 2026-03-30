var SHEET_NAME = "시트1";

function doGet(e) {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);

  // CORS 이슈 방지를 위한 응답 헤더 추가
  var headers = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET",
    "Access-Control-Allow-Headers": "Content-Type"
  };

  // 1. 데이터 조회 (Read) - JSON 배열 형식으로 반환
  if (e.parameter.action === 'getData') {
    var data = sheet.getDataRange().getValues();
    var items = [];

    // 첫 번째 행은 헤더(timestamp, menu)로 가정
    if (data.length > 1) {
      for (var i = 1; i < data.length; i++) {
        items.push({
          timestamp: data[i][0],
          menu: data[i][1]
        });
      }
    }

    return ContentService.createTextOutput(JSON.stringify({ "items": items }))
      .setMimeType(ContentService.MimeType.JSON);
  }

  // 2. 투표 기록 (Write) - 새 행 추가
  var selectedMenu = e.parameter.menu;
  if (selectedMenu) {
    sheet.appendRow([new Date(), selectedMenu]);
    return ContentService.createTextOutput(JSON.stringify({ "status": "success", "menu": selectedMenu }))
      .setMimeType(ContentService.MimeType.JSON);
  }

  return ContentService.createTextOutput(JSON.stringify({ "error": "Invalid request" }))
    .setMimeType(ContentService.MimeType.JSON);
}
