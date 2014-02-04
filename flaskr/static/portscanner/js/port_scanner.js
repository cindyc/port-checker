$(function() {
    /** Set up form submission behavior. */
    formEngine.registerSubmit("source_server_info", $("#submit_form"));
    $("#source_server_info").submit(function(event) {
        callEngine.doCall({
            url : "port_scan.json",
            settings : {
                success : function(data, textStatus, jqXHR) {
                    showScanResults(data);
                },
                error : function(jqXHR, textStatus, errorThrown) {
                    console.log(jqXHR);
                    var failureMessage = "Could not connect to server";
                    $("#scan_results").html(wrapWithTag(failureMessage, "p"));
                    alertEngine.showAlert({
                        alertBody : failureMessage,
                        alertClass : "error"
                    });
                }
            }
        });
    });
});

var showScanResults = function(scanResults) {
    var iconMap = {
        "open" : "icon-ok-sign",
        "closed" : "icon-minus-sign",
        "check firewall" : "icon-warning-sign"
    };
    console.log(scanResults);
    $("#scan_results").html("");
    //add server name and other related info
    forEach(scanResults, function(thisResult, portId) {
        var portList = [];
        forEach(thisResult, function(thisProtocol) {
            forEach(["inbound", "outbound"], function(thisConnection) {
               if (thisProtocol.hasOwnProperty(thisConnection)) forEach(thisProtocol[thisConnection], function(connectionStatus, connectionHost) {
                   portList.push(connectionHost);
               });
            });
        });
        portList = makeUniqueArray(portList);

        var resultTable = document.createElement("table");
        $(resultTable).attr("class", "table table-hover");
        $(resultTable).append('<thead></thead><tbody></tbody>');

        var headerString = "";
        forEach(["Port", "Protocol", "Connection"].concat(portList), function(thisCol) {
            headerString += wrapWithTag(thisCol, "th");
        });
        $(resultTable).find("thead").first().html(wrapWithTag(headerString, "tr"));

        forEach(thisResult, function(thisProtocol, protocolId) {
            forEach(["inbound", "outbound"], function(thisConnection) {
                if (thisProtocol.hasOwnProperty(thisConnection)) {
                    var rowData = [portId, makeNiceName(protocolId, true), makeNiceName(thisConnection, true)];
                    forEach(portList, function(thisPort) {
                        if (thisProtocol[thisConnection].hasOwnProperty(thisPort)) {
                            var iconClass = (iconMap.hasOwnProperty(thisProtocol[thisConnection][thisPort])) ? iconMap[thisProtocol[thisConnection][thisPort]] : "icon-warning-sign";
                            rowData.push(wrapWithTag(" ", "i", {"class":iconClass}));
                        } else {
                            rowData.push("-");
                        }
                    });
                    var rowText = "";
                    forEach(rowData, function(thisCell) {
                        rowText += wrapWithTag(thisCell, "td");
                    });

                    $(resultTable).find("tbody").first().append(wrapWithTag(rowText, "tr"));

                }
            });
        });

        $("#scan_results").append(resultTable);
    });
}