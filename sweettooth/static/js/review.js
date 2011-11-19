"use strict";

define(['jquery'], function($) {

    var REVIEW_URL_BASE = '/review/ajax';

    function addLineNumbers(data) {
        var $fileView, $table, $tr;

        $tr = $('<tr>');
        $table = $('<table>', {'class': 'filetable'}).append($tr);

        if (data.num_lines) {
            var count = data.num_lines;
            var lines = [];
            lines.push("<td class=\"linenumbers\"><pre>");
            for (var i = 1; i < (count + 1); i ++) {
                lines.push("<span rel=\"L" + i + "\">" + i + "</span>\n");
            }
            lines.push("</pre></td>");

            $tr.append(lines.join(''));
        }

        $fileView = $('<div>', {'class': 'file'}).
            appendTo($('<td>', {'width': '100%'}).appendTo($tr));

        $fileView.html(data.html);

        return $table;
    }

    function createFileView(filename, pk, diff) {
        var frag = diff ? '/get-file-diff/' : '/get-file/';

        var req = $.ajax({
            type: 'GET',
            dataType: 'json',
            data: { filename: filename },
            url: REVIEW_URL_BASE + frag + pk
        });

        var deferred = new $.Deferred();

        req.done(function(data) {
            var $html;
            if (diff) {
                if (data === null) {
                    $html = $('<p>', {'class': 'nochanges'}).
                        text("There have been no changes in this file.");
                } else {
                    var $old = addLineNumbers(data['old']);
                    var $new = addLineNumbers(data['new']);

                    $html = $('<table>', {'class': 'diff'});
                    var $tr = $('<tr>').appendTo($html);

                    $tr.append($('<td>', {'width': '50%',
                                          'class': 'code'}).append($old));
                    $tr.append($('<td>', {'width': '50%',
                                          'class': 'code'}).append($new));
                }
            } else {
                $html = addLineNumbers(data);
            }
            deferred.resolve($html);
        });

        return deferred;
    }

    $.fn.reviewify = function(diff) {
        var $elem = $(this);
        var $fileList = $('<ul>', {'class': 'filelist'}).appendTo($elem);
        var pk = $elem.data('pk');

        // Hide the file list until we're done grabbing all the elements.
        $fileList.hide();

        var $fileDisplay = $('<div>', {'class': 'filedisplay'}).appendTo($elem);
        $fileDisplay.css('position', 'relative');
 
        var currentFilename;
        var $currentFile = null;

        var req = $.ajax({
            type: 'GET',
            dataType: 'json',
            data: { disallow_binary: diff },
            url: REVIEW_URL_BASE + '/get-file-list/' + pk,
        });

        function showTable(filename, $file, $selector) {
            $fileList.find('li a.fileselector').removeClass('selected');
            $selector.addClass('selected');

            $file.css('position', 'relative');

            if ($currentFile != null) {
                $currentFile.css({'position': 'absolute',
                                  'top': '0'});
                $currentFile.fadeOut();
                $file.fadeIn();
            } else {
                $file.show();
            }

            currentFilename = filename;
            $currentFile = $file;
        }

        req.done(function(files) {
            function createFileSelector(tag, filename) {
                var $selector = $('<a>').
                    addClass(tag).
                    addClass('fileselector').
                    text(filename);

                var $file = null;

                $selector.click(function() {
                    if ($selector.hasClass('selected'))
                        return;

                    if ($file === null) {
                        var d = createFileView(filename, pk, diff);
                        currentFilename = filename;
                        d.done(function($table) {
                            $file = $table;
                            $file.hide().appendTo($fileDisplay);
                            if (currentFilename === filename)
                                showTable(filename, $file, $selector);
                        });
                    } else {
                        showTable(filename, $file, $selector);
                    }

                });

                $('<li>').append($selector).appendTo($fileList);
            }


            $.each(files.both, function() { createFileSelector('both', this); });
            $.each(files.added, function() { createFileSelector('added', this); });
            $.each(files.deleted, function() { createFileSelector('deleted', this); });

            $fileList.show();

            // Select the first item.
            $fileList.find('li a.fileselector').first().click();
        });
    };
});
