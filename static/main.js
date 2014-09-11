var toBeChecked;
var dependencyGraph;

// Functools
function reduce(iterable, start, callback) {
    $.each(iterable, function (key, value) {
        start = callback(start, value)
    });

    return start
}

function filter(iterable, callback) {
    var result;

    if ($.isArray(iterable)) {
        result = [];
        $.each(iterable, function (i, value) {
            if (callback(value))
                result.push(value)
        })
    }
    else {
        result = {};
        $.each(iterable, function (key, value) {
            if (callback(value))
                result[key] = value
        })
    }

    return result
}

function map(iterable, callback) {
    var result;

    if ($.isArray(iterable)) {
        result = [];
        $.each(iterable, function (i, value) {
            result.push(callback(value))
        })
    }
    else {
        result = {};
        $.each(iterable, function (key, value) {
            result[key] = callback(value)
        })
    }

    return result
}

// Rendering functions.
function toggleCheckbox($checkbox, isChecked) {
    $checkbox.prop('checked', isChecked);
}

function enableDisableCheckbox($checkbox, isEnabled) {
    $checkbox.prop('disabled', !isEnabled);
    if (!isEnabled)
        $checkbox.closest('tr').addClass('disabled');
    else
        $checkbox.closest('tr').removeClass('disabled')
}

// Terms' calculator functions.
function maxOfTotals() {
    var startValue = {'days': 0, 'workDays': 0};
    var arr = $.isArray(arguments[0]) ? arguments[0] : arguments;

    return reduce(arr, startValue, function(pTotal, cTotal) {
        return pTotal.days + pTotal.workDays >
            cTotal.days + cTotal.workDays ? pTotal : cTotal
    })
}

function calculateTotal(node) {
    function addUpTotals(a, b) {
        return {'days': a.days + b.days, 'workDays': a.workDays + b.workDays};
    }

    function recursiveHelper(node) {
        var currentTotal = {'days': 0, 'workDays': 0};
        if (node.checked) {
            currentTotal.days = node.days;
            currentTotal.workDays = node.workDays;
        }

        if (node.checked && node.children.length > 0) {
            var childrenTotals = map(node.children, function (nodeId) {
                return recursiveHelper(dependencyGraph[nodeId])
            });
            return addUpTotals(currentTotal, maxOfTotals(childrenTotals));
        }
        else
            return currentTotal
    }

    return recursiveHelper(node);
}

// Main function.
function manageDependencies(serviceId, isChecked) {
    /* Disable/enable checkboxes for services, when their dependencies are
     * checked or unchecked.
     */
    function walk(currentId, isChecked) {
        dependencyGraph[currentId].checked = isChecked;

        $.each(dependencyGraph[currentId].children, function(i, childId) {
            var child = dependencyGraph[childId];

            // If checkbox bound to the currentId is unchecked, all its
            // descendants must be unchecked and disabled.
            if (!isChecked) {
                child.checked = false;
                child.enabled = false;
                walk(childId, false);
            }
            // If checkbox bound to the serviceId is checked, all its children
            // must be enabled, but only if their other parents (if any) are
            // checked too.
            else {
                var mustEnableChild = reduce(child.parents, true,
                    function(pFlag, cId) {
                        return pFlag && dependencyGraph[cId].checked
                    });
                if (mustEnableChild)
                    child.enabled = true
            }
        });
    }

    // Calculate states.
    if (arguments.length == 0)   // on page load
        $.each(dependencyGraph, function (key) {
            walk(key, false)
        });
    else {
        walk(serviceId, isChecked)
    }

    // Calculate terms.
    var parentNodes = filter(dependencyGraph, function (value) {
        return value.parents.length === 0
    });
    var startValue = {'days': 0, 'workDays': 0};
    var totalDays = reduce(parentNodes, startValue, function (pTotal, node) {
        return maxOfTotals(pTotal, calculateTotal(node))
    });

    // Render.
    $('input[type=checkbox]').each(function() {
        enableDisableCheckbox($(this), dependencyGraph[this.id].enabled);
        toggleCheckbox($(this), dependencyGraph[this.id].checked);
    });
    $('#days-total').text(totalDays['days']);
    $('#work-days-total').text(totalDays['workDays'])
}

function bindCheckboxes() {
///    Bind checkboxes on a page to the dependency management routine.
    $('input[type=checkbox]').on("click", function () {
        var id = $(this).prop('id');
        // Current state of 'checked' must be reversed for this i.
        manageDependencies(id, !dependencyGraph[id].checked);
    });
}

if (dependencyGraph) {
    $(document).ready(function() {
        bindCheckboxes();
        // Run for the first time to disable checkboxes bound to services with
        // unsatisfied dependencies.
        manageDependencies()
    });
}

// Bootstrap accordion panel icons behaviour.
$(document).ready(function () {
   $('div.panel-group div.panel-collapse')
       .on("shown.bs.collapse hidden.bs.collapse", function () {
        $(this).prev().find("i.glyphicon")
            .toggleClass('glyphicon-chevron-down glyphicon-chevron-right')
   })
});

// Handlers for admin page buttons.
$(document).ready(function () {
   $('button#admin-btn-init').click(function () {
       ;
   });
   $('button#admin-btn-patch').click(function () {
       ;
   })
});