# Copyright 2008-2011 Nokia Networks
# Copyright 2011-2016 Ryan Tomac, Ed Manlove and contributors
# Copyright 2016-     Robot Framework Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from collections import namedtuple

from selenium.common.exceptions import (NoSuchWindowException,
                                        WebDriverException)

from SeleniumLibrary.base import ContextAware


WindowInfo = namedtuple('WindowInfo', 'handle, id, name, title, url')


class WindowManager(ContextAware):

    def __init__(self, ctx):
        self._strategies = {
            'title': self._select_by_title,
            'name': self._select_by_name,
            'url': self._select_by_url,
            None: self._select_by_default
        }
        ContextAware.__init__(self, ctx)

    def get_window_infos(self):
        infos = []
        try:
            starting_handle = self.browser.current_window_handle
        except NoSuchWindowException:
            starting_handle = None
        try:
            for handle in self.browser.window_handles:
                self.browser.switch_to.window(handle)
                infos.append(self._get_current_window_info(self.browser))
        finally:
            if starting_handle:
                self.browser.switch_to.window(starting_handle)
        return infos

    def select(self, locator):
        if locator is not None:
            if isinstance(locator, list):
                self._select_by_excludes(self.browser, locator)
                return
            if locator.lower() == "self" or locator.lower() == "current":
                return
            if locator.lower() == "new" or locator.lower() == "popup":
                self._select_by_last_index(self.browser)
                return
        (prefix, criteria) = self._parse_locator(locator)
        strategy = self._strategies.get(prefix)
        if strategy is None:
            raise ValueError("Window locator with prefix '" + prefix + "' is not supported")
        return strategy(self.browser, criteria)

    def _select_by_title(self, browser, criteria):
        self._select_matching(
            browser,
            lambda window_info: window_info[3].strip().lower() == criteria.lower(),
            "Unable to locate window with title '" + criteria + "'")

    def _select_by_name(self, browser, criteria):
        self._select_matching(
            browser,
            lambda window_info: window_info[2].strip().lower() == criteria.lower(),
            "Unable to locate window with name '" + criteria + "'")

    def _select_by_url(self, browser, criteria):
        self._select_matching(
            browser,
            lambda window_info: window_info[4].strip().lower() == criteria.lower(),
            "Unable to locate window with URL '" + criteria + "'")

    def _select_by_default(self, browser, criteria):
        if criteria is None or len(criteria) == 0 or criteria.lower() == "null":
            handles = browser.window_handles
            browser.switch_to.window(handles[0])
            return
        try:
            starting_handle = browser.current_window_handle
        except NoSuchWindowException:
            starting_handle = None
        for handle in browser.window_handles:
            browser.switch_to.window(handle)
            if criteria == handle:
                return
            for item in self._get_current_window_info(browser)[2:4]:
                if item.strip().lower() == criteria.lower():
                    return
        if starting_handle:
            browser.switch_to.window(starting_handle)
        raise ValueError("Unable to locate window with handle or name or title or URL '" + criteria + "'")

    def _select_by_last_index(self, browser):
        handles = browser.window_handles
        try:
            if handles[-1] == browser.current_window_handle:
                raise AssertionError("No new window at last index. Please use '@{ex}= | List Windows' + new window trigger + 'Select Window | ${ex}' to find it.")
        except IndexError:
            raise AssertionError("No window found")
        except NoSuchWindowException:
            raise AssertionError("Currently no focus window. where are you making a popup window?")
        browser.switch_to.window(handles[-1])

    def _select_by_excludes(self, browser, excludes):
        for handle in browser.window_handles:
            if handle not in excludes:
                browser.switch_to.window(handle)
                return
        raise ValueError("Unable to locate new window")

    def _parse_locator(self, locator):
        prefix = None
        criteria = locator
        if locator is not None and len(locator) > 0:
            locator_parts = locator.partition('=')
            if len(locator_parts[1]) > 0:
                prefix = locator_parts[0].strip().lower()
                criteria = locator_parts[2].strip()
        if prefix is None or prefix == 'name':
            if criteria is None or criteria.lower() == 'main':
                criteria = ''
        return (prefix, criteria)

    def _select_matching(self, browser, matcher, error):
        try:
            starting_handle = browser.current_window_handle
        except NoSuchWindowException:
            starting_handle = None
        for handle in browser.window_handles:
            browser.switch_to.window(handle)
            if matcher(self._get_current_window_info(browser)):
                return
        if starting_handle:
            browser.switch_to.window(starting_handle)
        raise ValueError(error)

    def _get_current_window_info(self, browser):
        try:
            id, name = browser.execute_script("return [ window.id, window.name ];")
        except WebDriverException:
            # The webdriver implementation doesn't support Javascript so we
            # can't get window id or name this way.
            id = name = None
        return WindowInfo(browser.current_window_handle,
                          id if id is not None else 'undefined',
                          name or 'undefined',
                          browser.title or 'undefined',
                          browser.current_url or 'undefined')
