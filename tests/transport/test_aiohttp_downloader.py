import pytest

from zakup_serv.infrastructure.urls import (
    URLRequest,
)
from zakup_serv.infrastructure.CustomExceptions import (
    NotRetriableNetworkException,
    ExceededRetryAttemptsException,
)
from zakup_serv.transport.base import WebLoaderConfig
import zakup_serv.settings as core_settings
from zakup_serv.transport.aiohttp_dl import AiohttpDlTransport

# TEST_OK_PAGE_URL = "https://example.com"
TEST_OK_PAGE_URL = "https://zakupki.gov.ru/epz/contract/search/results.html?morphology=on&fz44=on&contractStageList_0=on&contractStageList_1=on&contractStageList_2=on&contractStageList_3=on&contractStageList=0%2C1%2C2%2C3&selectedContractDataChanges=ANY&contractPriceFrom=0&contractPriceTo=1000000000000&budgetLevelsIdNameHidden=%7B%7D&customerPlace=44000000000&customerPlaceCodes=44000000000&contractDateFrom=01.01.2026&contractDateTo=01.05.2026&countryRegIdNameHidden=%7B%7D&sortBy=UPDATE_DATE&pageNumber=1&sortDirection=false&recordsPerPage=_50&showLotsInfoHidden=false"
TEST_FAIL_PAGE_URL = "https://example.com/fail"


@pytest.mark.asyncio
async def test_just_can_download_page_with_test_proxy():
    url = URLRequest(TEST_OK_PAGE_URL)

    web_loader_config = WebLoaderConfig(
        [
            url,
        ],
        proxy=core_settings.NET_DEFAULTS.get("PROXY", None),
    )

    page_loader = AiohttpDlTransport(web_loader_config)
    download_results = await page_loader.a_run()
    single_download_result = download_results[0]
    #  Длина ответа
    res_len = len(single_download_result.request_result)

    assert single_download_result.url_request.ok == True, f"запрос завершился неудачей"
    assert single_download_result.url_request.status_code in [
        200,
        299,
    ], f"запрос завершился с кодом {single_download_result.url_request.status_code}"
    assert res_len > 0, f"Размер тела ответа - {res_len} - говорит об ошибке"


@pytest.mark.asyncio
async def test_just_can_download_page_with_out_test_proxy():
    url = URLRequest(TEST_OK_PAGE_URL)

    web_loader_config = WebLoaderConfig(
        [
            url,
        ],
        proxy=None,
    )

    page_loader = AiohttpDlTransport(web_loader_config)
    download_results = await page_loader.a_run()
    single_download_result = download_results[0]
    #  Длина ответа
    res_len = len(single_download_result.request_result)

    assert single_download_result.url_request.ok == True, f"запрос завершился неудачей"
    assert single_download_result.url_request.status_code in [
        200,
        299,
    ], f"запрос завершился с кодом {single_download_result.url_request.status_code}"
    assert res_len > 0, f"Размер тела ответа - {res_len} - говорит об ошибке"


@pytest.mark.asyncio
async def test_must_brake_on_real_404():

    url = URLRequest(TEST_FAIL_PAGE_URL)

    web_loader_config = WebLoaderConfig(
        [
            url,
        ],
        proxy=None,
    )

    page_loader = AiohttpDlTransport(web_loader_config)
    download_results = await page_loader.a_run()
    single_download_result = download_results[0]

    #
    request_result = single_download_result.request_result
    request_error = single_download_result.downloading_raised_exceptions
    attempts = single_download_result.url_request.attempt

    assert (
        request_result is None
    ), "Результат должен быть None, т.к. запрос завершён с ошибкой"
    assert isinstance(request_error, NotRetriableNetworkException), (
        f"Ожидается NotRetriableNetworkError, " f"но получено {type(request_error)}"
    )
    assert attempts == 1, (
        f"Запрос с такой ошибкой должен "
        f"завершиться за 1 попытку, но фактически за {attempts}"
    )


@pytest.mark.asyncio
async def test_must_brake_on_fake_404():

    def http_404_generator():
        while True:
            yield 404

    url = URLRequest(TEST_OK_PAGE_URL)

    web_loader_config = WebLoaderConfig(
        [
            url,
        ],
        proxy=None,
    )

    page_loader = AiohttpDlTransport(web_loader_config)
    page_loader.fake_http_code_gen = http_404_generator

    download_results = await page_loader.a_run()
    single_download_result = download_results[0]

    request_result = single_download_result.request_result
    request_error = single_download_result.downloading_raised_exceptions
    attempts = single_download_result.url_request.attempt

    assert (
        request_result is None
    ), "Результат должен быть None, т.к. запрос завершён с ошибкой"
    assert isinstance(request_error, NotRetriableNetworkException), (
        f"Ожидается NotRetriableNetworkError, " f"но получено {type(request_error)}"
    )
    assert attempts == 1, (
        f"Запрос с такой ошибкой должен "
        f"завершиться за 1 попытку, но фактически за {attempts}"
    )


@pytest.mark.asyncio
async def test_must_brake_on_fake_503_with_several_attempts():

    def http_503_generator():
        while True:
            yield 503

    url = URLRequest(TEST_OK_PAGE_URL)
    max_attempts = core_settings.DEFAULT_RETRY_POLICY["retries"]

    web_loader_config = WebLoaderConfig(
        [
            url,
        ],
        proxy=None,
    )

    page_loader = AiohttpDlTransport(web_loader_config)
    page_loader.fake_http_code_gen = http_503_generator

    download_results = await page_loader.a_run()
    single_download_result = download_results[0]

    request_result = single_download_result.request_result
    request_error = single_download_result.downloading_raised_exceptions
    attempts = single_download_result.url_request.attempt

    assert (
        request_result is None
    ), "Результат должен быть None, т.к. запрос завершён с ошибкой"
    assert isinstance(request_error, ExceededRetryAttemptsException), (
        f"Ожидается ExceededRetryAttemptsError, " f"но получено {type(request_error)}"
    )
    assert attempts == max_attempts, (
        f"Запрос с такой ошибкой должен "
        f"завершиться за 1 попытку, но фактически за {attempts}"
    )


@pytest.mark.asyncio
async def test_must_succsess_on_last_atteprt_on_fake_502():
    max_attempts = core_settings.DEFAULT_RETRY_POLICY["retries"]

    def http_502_and_200_generator():
        yield 502
        yield 200

    url = URLRequest(TEST_OK_PAGE_URL)

    web_loader_config = WebLoaderConfig(
        [
            url,
        ],
        proxy=None,
    )

    page_loader = AiohttpDlTransport(web_loader_config)
    page_loader.fake_http_code_gen = http_502_and_200_generator

    download_results = await page_loader.a_run()
    single_download_result = download_results[0]

    request_result = single_download_result.request_result
    request_error = single_download_result.downloading_raised_exceptions
    attempts = single_download_result.url_request.attempt

    assert (
        request_result is not None
    ), "Результат должен быть, т.к. запрос завершён успешно"
    assert request_error is None, (
        f"Поле с ошибкой запроса должно быть пустым, " f"т.к. запрос завершился удачно"
    )
    assert attempts == 2, (
        f"Запрос с такой ошибкой должен "
        f"завершиться за 2 попытки, но фактически за {attempts}"
    )
