// ==UserScript==
// @name         HoboGet720p
// @namespace    http://lintd233.xyz/
// @version      0.1
// @description  Get 720p back for hobo(s)
// @author       You
// @match        https://www.bilibili.com/video/*
// @icon         https://www.google.com/s2/favicons?domain=bilibili.com
// @grant        none
// @require      https://cdn.bootcdn.net/ajax/libs/jquery/3.6.0/jquery.min.js
// ==/UserScript==

(function() {
    'use strict';

    function f0() {
        function f1(a) {
            a.login = 1;
            return false;
        }
        window.player.reloadAccess(f1);
        $('div.bilibili-player-video-quality-menu li[data-value="64"]').click();
    }
    function f2() {
        try {
            f0();
        } catch (e) {
            console.error('hobo failure', e);
            setTimeout(f2, 5000);
        }
    }
    setTimeout(f2, 5000);
})();