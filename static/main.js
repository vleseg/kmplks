var dependencyGraph;

// Ajax loading indicator show/hide
$.ajaxSetup({
    beforeSend:function(){
        $("#loading").show();
    },
    complete:function(){
        $("#loading").hide();
    }
});

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

// Various Bootstrap behaviour snippets go here.
$(document).ready(function () {
    // Accordion panel icons behaviour.
    $('div.panel-group div.panel-collapse')
       .on("show.bs.collapse hidden.bs.collapse", function () {
        $(this).prev().find("i.glyphicon")
            .toggleClass('glyphicon-chevron-down glyphicon-chevron-right')
        });
    // Admin list logic
    if (window.location.href.indexOf('admin/list') > -1) {
        $("a[data-toggle='tab']").on("shown.bs.tab", function(e) {
            var reqKind = $(this).attr('href').slice(1);
            var tabPaneContent = $('#' + reqKind).find('.tab-pane-items');
            $('#list-name-pl').find('small').text($(this).text().toUpperCase());

            $.getJSON('/admin/api/list', {'kind': reqKind}, function (data) {
                tabPaneContent.empty();

                // list container
                var listContainer = jQuery(
                    '<div/>', {class: 'list-group'}
                ).appendTo(tabPaneContent);

                // 'add new item' button
                $('<a/>', {
                    href: '/admin/create?kind=' + reqKind,
                    class: 'list-group-item list-group-item-success',
                    text: '+ Создать'
                }).insertBefore(listContainer);

                // iterating data to fill list container
                $.each(data, function (i, item) {
                    var listItem = $('<div/>', {
                        class: 'list-group-item'
                    }).appendTo(listContainer);

                    // item link
                    $('<a/>', {
                        href: '/admin/entity?id=' + item.id,
                        target: '_blank',
                        text: item.value
                    }).appendTo(listItem);

                    // delete link and icon
                    $('<a/>', {
                        // TODO: think how uri_for can be used here
                        href: '/admin/delete?id=' + item.id,
                        target: '_blank',
                        class: 'pull-right',
                        title: 'Удалить'
                    }).append($('<i/>', {
                        class: 'glyphicon glyphicon-remove text-danger'
                    })).appendTo(listItem);
                })
            }).fail(function (xhr, status, error) {
                var msg = jQuery('<div/>', {
                    class: 'alert alert-danger',
                    role: 'alert'
                });
                $('<h4/>', {text: 'Ошибка!'}).appendTo(msg);
                $('<p/>', {
                    'text': 'Во время получения списка произошла ошибка: ' +
                        status + ', ' + error + '.'
                }).appendTo(msg);

                tabPaneContent.empty().append(msg);
            })
        });

        $('#tabs').find('a[href=#Service]').tab('show')
    }
});