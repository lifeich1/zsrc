// ==UserScript==
// @name         Kill-Login-Guide
// @namespace    http://lintd.xyz/
// @version      0.1
// @description  try to take over the world!
// @author       You
// @include      https://live.bilibili.com/0*
// @include      https://live.bilibili.com/1*
// @include      https://live.bilibili.com/2*
// @include      https://live.bilibili.com/3*
// @include      https://live.bilibili.com/4*
// @include      https://live.bilibili.com/5*
// @include      https://live.bilibili.com/6*
// @include      https://live.bilibili.com/7*
// @include      https://live.bilibili.com/8*
// @include      https://live.bilibili.com/9*
// @icon         https://www.google.com/s2/favicons?domain=bilibili.com
// @grant        none
// ==/UserScript==



(function() {
    'use strict';

    function getcookie_n(name) {
        var ca = document.cookie.split(';');
        for(var i=0; i<ca.length; i++)
        {
            var c = ca[i].trim();
            if (c.indexOf(name)==0) return parseInt(c.substring(name.length,c.length));
        }
        return 0;
    };
    if (0 == getcookie_n('DedeUserID')) {
        document.cookie = 'DedeUserID=1';
    }

    function just_one_more_check_kill() {
        if (!check_kill_login_guide()) {
            setTimeout(check_kill_login_guide, 5000);
        }
    }

    function check_kill_login_guide() {
        console.log('killing login guide');
        try {
            document.getElementById('switch-login-guide-vm').setAttribute('hidden', true);
            document.getElementById('my-dear-haruna-vm').setAttribute('hidden', true);
            return true;
        } catch (e) {
            console.error('try to kill login guide failure', e);
            return false;
        }
    }

    just_one_more_check_kill();
})();