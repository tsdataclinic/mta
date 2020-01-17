const fs = require('fs');
var endOfMonth = require('date-fns/endOfMonth');
var addMonths = require('date-fns/addMonths');
var addDays = require('date-fns/addDays');
var format = require('date-fns/format');

const puppeteer = require('puppeteer');
const args = process.argv.slice(2);

const year = args[0] ? args[0] : 2018;

const parse_range = async (start_date, end_date, outfile) => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  await page.goto('https://mymtaalerts.com/messagearchive.aspx');

  let all_data = [];
  let pages = 10;
  let count = 0;

  await page.click('#ctl00_ContentPlaceHolder1_dtpStartDate_dateInput', {
    clickCount: 3,
  });
  await page.type(
    '#ctl00_ContentPlaceHolder1_dtpStartDate_dateInput',
    start_date,
  );

  await page.click('#ctl00_ContentPlaceHolder1_dtpStopDate_dateInput', {
    clickCount: 3,
  });
  await page.type('#ctl00_ContentPlaceHolder1_dtpStopDate_dateInput', end_date);

  await page.screenshot({path: `before_get_data.png`});

  page.click('#ctl00_ContentPlaceHolder1_btnGetData');
  await page.waitForNavigation();

  while (true) {
    console.time('parse page');
    let {page_data, current_page, total_pages} = await page.evaluate(() => {
      const elementsToArray = el_list => Array.prototype.slice.call(el_list);
      let table = document.querySelector('table.rgMasterTable > tbody');
      let current_page = document.querySelector('a.rgCurrentPage > span')
        .innerText;
      let total_pages = document.querySelector(
        '.rgInfoPart > strong:nth-child(2)',
      ).innerText;
      let rows = elementsToArray(table.getElementsByTagName('tr'));
      let pdata = rows.map(r =>
        elementsToArray(r.getElementsByTagName('td')).map(e => e.innerText),
      );
      return {
        page_data: pdata,
        current_page: current_page,
        total_pages: total_pages,
      };
    });

    console.log('current page ', current_page, ' of ', total_pages);
    all_data = all_data.concat(page_data);

    if (current_page == total_pages) {
      break;
    }

    console.timeEnd('parse page');
    console.time('page load');
    page.click('input.rgPageNext');
    await page.waitForNavigation();
    console.timeEnd('page load');
    //await page.screenshot({path: `page_${count}.png`});
    console.log();
    count += 1;
  }
  console.log(all_data.length);

  fs.writeFileSync(outfile, JSON.stringify(all_data));
  await browser.close();
};

(async () => {
  let start_date = new Date(year, 0, 1);

  for (let month = 0; month < 12; month++) {
    let start = addMonths(start_date, month);

    let end = addDays(endOfMonth(start), -1);
    let start_string = format(start, 'MM/dd/yyyy');
    let end_string = format(end, 'MM/dd/yyyy');
    let outfile =
      'data/' +
      format(start, 'MM_dd_yyyy') +
      '-' +
      format(end, 'MM_dd_yyyy') +
      '.json';
    if (fs.existsSync(outfile)) {
      console.log('done and skipping ', outfile);
    } else {
      await parse_range(start_string, end_string, outfile);
    }

    //  parse_range(start_date,end_date);
  }
})();
