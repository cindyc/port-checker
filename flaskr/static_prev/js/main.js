/** remote call handler. */
var callEngine;
var CallBox = function() {
    var that = this;

    /**
        remote caller.
        @param {object} nextCallInfo - overriding call object.
    */
    this.doCall = function(nextCallInfo) {
        /** Base call payload object; typically overridden by nextCallInfo.settings. */
        var callPayload = {
            dataType : "json",
            headers : {
                "accept" : "application/json"
            },
            success : function(data, textStatus, jqXHR) {},
            error : function(jqXHR, textStatus, errorThrown) {},
            complete : function(jqXHR, textStatus) {}
        };

        /** If nextCallInfo has a "settings" property, override callPayload data with the property value data. */
        if (nextCallInfo.hasOwnProperty("settings")) $.extend(true, callPayload, nextCallInfo.settings);

        /** Make the ajax call. */
        //$.ajax(that.baseUrl+nextCallInfo.url, callPayload);
        $.ajax(nextCallInfo.url, callPayload);
    };

    this.init = function() {
        //CHANGE THIS TO REFLECT THE ACTUAL LOCATION OF THE BACKEND PROCESS
        that.baseUrl = "/";
    }();
};

/** Alert display mechanism. */
var alertEngine;
var AlertBox = function() {
    var that = this;

    /**
        Takes an alert object with optional title, body, and class, and displays it.
        @param {object} messageObject - the message object.
    */
    this.showAlert = function(messageObject) {
        var messageHtml = "";
        if (messageObject.hasOwnProperty("alertTitle")) messageHtml += "<strong>"+messageObject.alertTitle+"</strong>";
        if (messageObject.hasOwnProperty("alertBody")) messageHtml += messageObject.alertBody;
        var alertClass = (messageObject.hasOwnProperty("alertClass")) ? " alert-"+messageObject.alertClass : "";

        /** If the message is greater than 120 characters or has embedded paragraph tags, use the "alert-block" class for improved appearance. */
        if ((messageHtml.length > 120) || (messageHtml.indexOf("<p>") > -1)) alertClass += " alert-block";

        /** Clear any existing alerts and show this new one. */
        that.clearAlerts();
        $(that.alertWrapper).prepend('<div class="alert_wrapper"><div class="alert_wrapper_inner"><div class="alert'+alertClass+'"><div class="alert-inner"><button type="button" class="close" data-dismiss="alert">&times;</button>'+messageHtml+'</div></div></div></div>');

        /** When an alert's "close" button is clicked, clear all page alerts. */
        $(that.alertWrapper+" .alert .close").click(function(event) {
            that.clearAlerts();
        });

    }

    /**
        Store an alert in Session Storage for retrieval on a subsequent page.
        @param {object} messageObject - the message object.
    */
    this.setAlert = function(messageObject) {
        var messageString = JSON.stringify(messageObject);
        sessionStorage.setItem("alert", messageString);
    };

    /**
        If there is an alert in Session Storage, show it and then clear it.
        @see showAlert.
    */
    this.getAlert = function() {
        var sessionAlert = (sessionStorage.getItem("alert")) || false;
        if (sessionAlert) {
            var messageObject = JSON.parse(sessionAlert);
            that.showAlert(messageObject);
            sessionStorage.removeItem("alert");
        }
    };

    /** Clear any existing alerts. */
    this.clearAlerts = function() {
        $(that.alertWrapper+" div.alert_wrapper").remove();
    };

    /**
        Establish container for alert messages and check for alerts in Session Storage.
        @see getAlert.
    */
    var init = function() {
        that.alertWrapper = "body";
        that.getAlert();
    }();

};

/** URL handler. */
var urlEngine;
var UrlBox = function() {
    var that = this;

    /**
        Set the working URL.
        @param {string} theUrl - the URL to work with.
    */
    this.setUrl = function(theUrl) {
        that.workingUrl = theUrl;
    };

    /**
        Get all parameters from a URL, and return them as an object.
        If a URL is not supplied, use the UrlBox instance's working URL.
        @param {string} [theUrl=workingUrl] - the URL to work with.
        @returns {object} paramObject - the URL parameters.
    */
    this.getParams = function(theUrl) {
        var theUrl = theUrl || that.workingUrl;
        var paramObject = {};
        var urlArray = theUrl.split("?");
        var urlPath = urlArray.shift();
        var urlParams = (urlArray.length > 0) ? urlArray.join("?").split("&") : [];
        forEach(urlParams, function(thisPair) {
            var pairArray = thisPair.split("=");
            var pairKey = pairArray.shift();
            var pairVal = (pairArray.length > 0) ? pairArray.join("=") : null;
            paramObject[pairKey] = pairVal;
        });
        return paramObject;
    };

    /**
        Add params to a URL and return it.
        @param {object} newParams - the parameters/values to add.
        @param {string} theUrl - the URL to work with.
        @returns {string} - the URL with new params.
    */
    this.setParams = function(newParams, theUrl) {
        var theUrl = theUrl || that.workingUrl;
        theUrl = theUrl.split("?")[0] + "?";
        var paramArray = [];
        forEach(newParams, function(paramValue, paramKey) {
            paramArray.push(paramKey+"="+paramValue);
        });
        return theUrl + paramArray.join("&");
    };

    /**
        Return the value of a given URL param.
        @param {string} paramKey - the parameter key.
        @param {string} theUrl - the URL to work with.
        @returns {string} paramVal - the value of the URL parameter.
    */
    this.getParam = function(paramKey, theUrl) {
        var theUrl = theUrl || that.workingUrl;
        var allParams = that.getParams(theUrl);
        var paramVal = (allParams.hasOwnProperty(paramKey)) ? allParams[paramKey] : false;
        return paramVal;
    };

    /**
        Create/Set the value of a given URL param.
        @param {string} paramKey - the parameter key.
        @param {string} paramValue - the parameter value.
        @param {string} theUrl - the URL to work with.
        @returns {string} - the URL with the new parameter set.
    */
    this.setParam = function(paramKey, paramValue, theUrl) {
        var theUrl = theUrl || that.workingUrl;
        var allParams = that.getParams(theUrl);
        allParams[paramKey] = paramValue;
        return that.setParams(allParams, theUrl);
    }

    /**
        Try to add a new param to the current URL.
        If the attempt fails, refresh the page with the modified URL.
    */
    this.setCurrentParam = function(paramKey, paramValue) {
        var newUrl = that.setParam(paramKey, paramValue, that.workingUrl);
        try {
            history.pushState({}, "", newUrl);
        } catch (e) {
            document.location.href = newUrl;
        }
    }

    /**
        Try to remove a param from the current URL.
        If the attempt fails, refresh the page with the modified URL.
    */
    this.clearCurrentParam = function(paramKey) {
        var newUrl = that.clearParam(paramKey, that.workingUrl);
        try {
            history.pushState({}, "", newUrl);
        } catch (e) {
            document.location.href = newUrl;
        }
    }

    /**
        Clear a given URL param.
        @param {string} paramKey - the parameter key.
        @param {string} theUrl - the URL to work with.
        @returns {string} - the URL with the parameter removed.
    */
    this.clearParam = function(paramKey, theUrl) {
        var theUrl = theUrl || that.workingUrl;
        var allParams = that.getParams(theUrl);
        if (allParams.hasOwnProperty(paramKey)) delete allParams[paramKey];
        return that.setParams(allParams, theUrl);
    }

    /**
        Get the filename from a given URL; assumes "index.html" if there's no filename in the URL.
        @param {string} [theUrl] - the URL to work with.
        @returns {string} - the file name.
    */
    this.getFilename = function(theUrl) {
        var theUrl = theUrl || that.workingUrl;
        var rawFileName = theUrl.substring(theUrl.lastIndexOf("/") + 1, theUrl.length).split("?")[0].split("#")[0];
        return (rawFileName.length > 0) ? rawFileName : "index.html";
    }

    var init = function() {

        /** Set this instance's working URL to be the document location. */
        that.setUrl(document.location.href);

    }();
}

/** Link handler. */
var linkEngine;
var LinkBox = function() {
    var that = this;
    this.setClicks = function(theContext) {
        var theContext = theContext || that.workingContext;

        /** Don't allow disabled links to return. */
        $(theContext+" a").click(function(event) {
            if ($(this).hasClass("disabled")) return false;
        });

        /** Any link with the "js_doPopup" class will open in a new window. */
        $(theContext+" a.js_doPopup").click(function(event) {
            window.open($(this).attr("href"));
            return false;
        });

        /** Any link with the "js_popModal" class will launch the first modal contained by the link parent div. */
        $(theContext+" a.js_popModal").click(function(event) {

            /** Clear any alert boxes when a modal is shown */
            alertEngine.clearAlerts();
            var targetModalId = $(this).attr("data-targetModalId") || false;
            var targetModal = (targetModalId) ? $("#"+targetModalId) : ($(this).closest("div").find(".modal")[0] || false);
            if (targetModal) {

                /** Save the referring link in the modal. */
                $(targetModal).data("launchingLink", $(this));
                $(targetModal).find("input").val("");

                /** Show the modal. */
                $(targetModal).modal("show");

            }
            return false;
        });

        /**
            Move url params to session storage params before following the link.
            @see UrlBox.getParams.
        */
        $(theContext+" a.js_storeParams").click(function(event) {
            var thisHref = $(this).attr("href");
            var paramsToStore = urlEngine.getParams(thisHref);
            forEach(paramsToStore, function(paramValue, paramKey) {
                sessionStorage.setItem(paramKey, paramValue);
            });
            document.location.href = thisHref.split("?")[0];
            return false;
        });

    }

    var init = function() {
        that.workingContext = "body";
        that.setClicks(that.workingContext);
    }();
};

/** Form builder and handler. */
var formEngine;
var FormBox = function() {
    var that = this;

    /**
        Set up the submit button and core submission functionality.
        @param {string} formId - the HTML ID of the form.
        @param {string} theSubmit - the Submit button/link identifier.
    */
    this.registerSubmit = function(formId, theSubmit) {

        /**
            Enable/disable submit button based on form validation check.
            @see checkForFullFields.
        */
        var inputAndSelectCheck = function() {
            if (that.checkForFullFields($("#"+formId))) {
                $(theSubmit).removeClass("disabled");
            } else {
                $(theSubmit).addClass("disabled");
            }
        }

        /** Check form "required" elements on input/select keyup/change events. */
        $('#'+formId+' input[required="required"]').unbind("keyup");
        $('#'+formId+' select[required="required"]').unbind("change");
        $('#'+formId+' input[required="required"]').keyup(function(event) {
            inputAndSelectCheck();
        });
        $('#'+formId+' select[required="required"], #'+formId+' input[type="checkbox"]').change(function(event) {
            inputAndSelectCheck();
        });
        $('#'+formId+' input[type="radio"]').click(function(event) {
            inputAndSelectCheck();
        });

        /** Submit button setup. */
        $(theSubmit).unbind("click");
        $(theSubmit).click(function(event) {

            /** Code is only fired if the button is not "disabled." */
            if (!$(this).hasClass('disabled')) {
                alertEngine.clearAlerts();
                $('#'+formId).submit();
            }

            return false;
        });

        /** Capturing enter key for form submission. */
        $(document).keydown(function(event) {
            if ((event.keyCode === 13) && ($("body").find("form").length < 2)) {
                $('#'+formId).submit();
                return false;
            }
        });

        inputAndSelectCheck();
    };

    /**
        If an input fails validation, show the error (and an optional message) inline.
        @param {string} theInput - the Input identifier.
        @param {string} [theMessage] - The optional error message.
        @param {boolean} [showMessage] - Optionally show message.
    */
    this.showBadInput = function(theInput, theMessage, showMessage) {
        var theMessage = theMessage || false;
        var showMessage = showMessage || false;
        if (theMessage) {
            $(theInput).attr("data-error_message", theMessage);
            if (showMessage) {
                 var parentControls = $(theInput).closest(".controls");
                 var parentHelp = $(parentControls).find(".help-inline");
                 if ($(parentHelp).length === 0) {
                    $(parentControls).append('<span class="help-inline">'+theMessage+'</span>');
                } else {
                    $(parentHelp).text(theMessage);
                }
            }
        }
    };

    /**
        If a form fails validation, alert the error message(s).
        @param {string} theForm - form identifier.
    */
    this.alertErrors = function(theForm) {
        /**
            Find any "error" inputs and add them to the errorList array.
            @see showBadInput.
        */
        var errorList = [];
        $(theForm).find(".error").each(function() {
            $(this).find("input[data-error_message], select[data-error_message], textarea[data-error_message]").each(function() {
                var errorText = $(this).attr("data-error_message");
                if ($.inArray(errorText, errorList) === -1) errorList.push(errorText);
            });
        });

        /**
            If errors are found, build an error message and a corresponding alert.
            @see AlertBox.showAlert.
        */
        if (errorList.length > 0) {
            var listString = "<br /><ul>";
            forEach(errorList, function(thisItem) {
                listString += '<li>'+thisItem+'</li>';
            });
            alertEngine.showAlert({
                alertTitle : "We're sorry.",
                alertBody : listString+"</ul>",
                alertClass : "error"
            });
        }

    };

    /**
        Make sure we are dealing with an email address.
        @param {string} theInputValue - the value to test.
        @returns {boolean} - validation result.
    */
    this.validateEmail = function(theInputValue) {
        var reg = /^([A-Za-z0-9_\-\.+])+\@([A-Za-z0-9_\-\.])+\.([A-Za-z]{2,4})$/;
        return (reg.test(theInputValue));
    };

    /**
        Make sure "required" inputs are non-empty.
        @param {string} theForm - form identifier.
        @returns {boolean} fieldsAreFull - validation result.
    */
    this.checkForFullFields = function(theForm) {
        var fieldsAreFull = true;
        $(theForm).find("input, select, textarea").each(function() {
            var isEmpty = ($(this).attr("type") === "checkbox") ? !$(this).prop('checked') : (!$.trim($(this).val()) || ($.trim($(this).val()) === ""));
            if ($(this).attr("type") === "radio") {
                isEmpty = true;
                var radioName = $(this).attr("name");
                $(theForm).find('input[name="'+radioName+'"]').each(function() {
                    if ($(this).prop('checked')) isEmpty = false;
                });
            }
            if ($(this).attr("required") && isEmpty) {
                fieldsAreFull = false;
                return false;
            };
        });
        return fieldsAreFull;
    };

    /**
        Call previously-defined validation functions.
        @see showBadInput.
        @param {string} theForm - form identifier.
        @returns {boolean} formIsGood - validation result.
    */
    this.validateForm = function(theForm) {
        var formIsGood = true;
        $(theForm).find("input, select, textarea").each(function() {
            $(this).closest(".control-group").removeClass("error");
            var isEmpty = ($(this).attr("type") === "checkbox") ? !$(this).prop('checked') : (!$(this).val() || ($(this).val() === ""));
            if ($(this).attr("required")) {
                if (($(this).attr("type") && ($(this).attr("type").toLowerCase() === "email")) && (!that.validateEmail($(this).val()))) {
                    formIsGood = false;
                    that.showBadInput($(this), 'Must be a valid email format');
                    $(this).closest(".control-group").addClass("error");
                } else if (isEmpty) {
                    formIsGood = false;
                    that.showBadInput($(this), 'Must not be blank');
                    $(this).closest(".control-group").addClass("error");
                }
            }
            if ($(this).attr("maxlength") && ($(this).val().length > parseInt($(this).attr("maxlength")))) {
                formIsGood = false;
                that.showBadInput($(this), 'Value exceeds maximum length');
                $(this).closest(".control-group").addClass("error");
            }
        });
        var passwordFields = $(theForm).find("[type='password']");
        if ((($(passwordFields).length > 1) && ($(passwordFields).eq(1).attr("id").indexOf("confirm") !== -1)) && ($(passwordFields).eq(0).val() !== $(passwordFields).eq(1).val())) {
            formIsGood = false;
            that.showBadInput($(passwordFields).eq(0), 'Passwords must match');
            $(passwordFields).eq(0).closest(".control-group").addClass("error");
            that.showBadInput($(passwordFields).eq(1));
            $(passwordFields).eq(1).closest(".control-group").addClass("error");
        }
        that.alertErrors(theForm);
        return formIsGood;
    };

    var init = function() {

        /** When an input is focused, changed, or clicked, remove the error state and clear any alerts. */
        $("input, textarea, select").on("focus, change, click", function() {
            if ($(this).closest(".control-group") && $(this).closest(".control-group").hasClass("error")) {
                $(this).closest(".controls").find(".help-inline").remove();
                $(this).closest(".control-group").removeClass("error");
            }
            $(this).removeAttr("data-error_message");
            alertEngine.clearAlerts();
        });

        /**
            When a form is submitted, return false.
            This is typically augmented by form-specific code elsewhere.
        */
        $("form").submit(function() {
            return false;
        });

    }();
}

/** Utility Functions. */
/**
    Iterate through an object, performing the specified function on each property.
    @param {object} theObject - the object to iterate through.
    @param {object} theFunction - the function to execute on each property.
*/
var forEach = function(theObject, theFunction) {
    for (var theKey in theObject) {
        if (theObject.hasOwnProperty(theKey)) theFunction(theObject[theKey], theKey);
    }
};

/**
    Return a code-safe version of a supplied string.
    @param {string} rawName - the raw string.
    @returns {string} - the code-safe version of the string.
*/
var makeSafeName = function(rawName) {
    return $.trim(rawName).replace(/\s+/g," ").toLowerCase();
};

/**
    Make a human-friendly version of a supplied string.
    @param {string} rawName - the raw string.
    @param {boolean} [makeCaps] - test individual words against a map of words with special capitalization.
    @returns {string} - the human-friendly version of the string.
*/
var makeNiceName = function(rawName, makeCaps) {
    var makeCaps = makeCaps || false;
    var capsMap = {
        "ip" : "IP",
        "id" : "ID",
        "url" : "URL",
        "uri" : "URI",
        "vdc" : "VDC",
        "os" : "OS",
        "tcp" : "TCP",
        "udp" : "UDP"
    };
    var niceWords = [];
    var rawWords = $.trim(rawName.toLowerCase()).split("_");
    forEach(rawWords, function(thisWord) {
        var niceWord = (makeCaps && capsMap.hasOwnProperty(thisWord)) ? capsMap[thisWord] : thisWord.substr(0,1).toUpperCase() + thisWord.substr(1);
        niceWords.push(niceWord);
    });
    return niceWords.join(" ");
}

/**
    Wraps the given text with the given tag.
    @param {string} theText - The text to wrap.
    @param {string} theTag - The tag name to wrap around the text.
    @param {object} tagAttributes - Optional attributes (like class, id, etc.) to be added to the tag.  Multiple values should be sent as an array.
    @returns {string} theText - formatted message.
    @see forceArray.
*/
var wrapWithTag = function(theText, theTag, tagAttributes) {
    var theText = theText || '';
    var theTag = (theTag) ? $.trim(theTag).toLowerCase() : false;
    var tagAttributes = tagAttributes || false;
    var attributesString = '';
    if (tagAttributes) {
        var attributesArray = [];
        forEach(tagAttributes, function(attributeValue, attributeKey) {
            attributesArray.push(attributeKey+'="'+forceArray(attributeValue).join(" ")+'"');
        });
        attributesString = ' '+attributesArray.join(" ");
    }
    if (theTag) {
        if (theText !== '') {
            theText = '<'+theTag+attributesString+'>'+theText+'</'+theTag+'>';
        } else {
            theText = '<'+theTag+attributesString+' />';
        }
    }
    return theText;
}

/**
    Formats date string.
    @param {string} theDate - the Date to be formatted.
    @param {boolean} [getMs] - optional flag to get epoch milliseconds instead of a formatted date.
    @returns {string} - the formatted date.
*/
var formatDate = function(theDate, getMs) {
    var getMs = getMs || false;
    var prettyDate = theDate;
    var theDate = ((typeof theDate === 'string') || (typeof theDate === 'number')) ? new Date(theDate) : theDate;
    if (theDate instanceof Date) {
        if (getMs) {
            prettyDate = theDate.getTime();
        } else {
            prettyDate = padDigit(theDate.getMonth() + 1) +'/'+ padDigit(theDate.getDate()) +'/'+ theDate.getFullYear();
        }
    }
    return prettyDate;
}

/**
    Formats date string, including timestamp.
    @param {string} theDate - the Date to be formatted.
    @returns {string} - the formatted date.
*/
var formatTime = function(theDate) {
    var prettyDate = theDate;
    var theDate = ((typeof theDate === 'string') || (typeof theDate === 'number')) ? new Date(theDate) : theDate;
    if (theDate instanceof Date) {
        prettyDate = padDigit(theDate.getMonth() + 1) +'/'+ padDigit(theDate.getDate()) +'/'+ theDate.getFullYear() + " " + [padDigit(theDate.getHours()), padDigit(theDate.getMinutes()), padDigit(theDate.getSeconds())].join(":");
    }
    return prettyDate;
}

/**
    Pads single-digit numbers with a leading zero.
    @param {number} rawNumber - the number to pad.
    @returns {int} - the padded number.
*/
var padDigit = function(rawNumber) {
    var rawNumber = parseInt(rawNumber);
    return (rawNumber < 10) ? '0'+rawNumber : rawNumber;
}

/**
    Force a unique array.
    @param {array} rawArray - the raw array.
    @returns {array} cleanArray - the unique array.
*/
var makeUniqueArray = function(rawArray) {
    var cleanArray = [];
    forEach(rawArray, function(rawValue) {
        if ($.inArray(rawValue, cleanArray) === -1) cleanArray.push(rawValue);
    });
    return cleanArray;
};

/**
    Force a supplied item to be an array, if it is not already one.
    @param {string|array|object} rawItem - the raw item.
    @returns {array} - the forced array.
*/
var forceArray = function(rawItem) {
    return ($.isArray(rawItem)) ? rawItem : [rawItem];
}

/** Code to be invoked when the DOM is ready, but typically before page assets have finished loading. */
$(function() {
    pageId = $("body").attr("id") || false;
    callEngine = new CallBox();
    alertEngine = new AlertBox();
    linkEngine = new LinkBox();
    formEngine = new FormBox();
    urlEngine = new UrlBox();
});
