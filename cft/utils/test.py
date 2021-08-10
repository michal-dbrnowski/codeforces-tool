import shutil
import subprocess

import bs4
import requests

from .constants import *


def test(args):
    contest, problem_letter = translate_problem_name(args.problem)
    problem = contest + problem_letter

    if not os.path.exists('in'):
        os.makedirs('in')
    if not os.path.exists('ans'):
        os.makedirs('ans')

    if args.download:
        for file in os.listdir('in'):
            os.remove(os.path.join('in', file))
        for file in os.listdir('ans'):
            os.remove(os.path.join('ans', file))

    if len(os.listdir('in')) == 0:
        r = requests.get(f'https://codeforces.com/problemset/problem/{contest}/{problem_letter}')
        try:
            r.raise_for_status()
        except requests.HTTPError:
            print(error_style('Something went wrong while downloading tests'))
            sys.exit()

        soup = bs4.BeautifulSoup(r.text, 'html.parser')
        tests_input = soup.select('div.sample-test div.input pre')
        tests_answer = soup.select('div.sample-test div.output pre')
        for i, (test_in, test_ans) in enumerate(zip(tests_input, tests_answer), start=1):
            with open(os.path.join('in', f'{i}.in'), 'w') as input_file:
                input_file.write(test_in.string.lstrip())
            with open(os.path.join('ans', f'{i}.out'), 'w') as answer_file:
                answer_file.write(test_ans.string.strip())

    compile_command = get_compile_command()
    if compile_command:
        if compile_solution(problem, compile_command).returncode != 0:
            print(error_style('Solution has not been compiled.'))
            sys.exit()
        else:
            print('Solution has been compiled.')

    i = 1
    while os.path.exists(os.path.join('in', f'{i}.in')):
        test_solution(problem, i, args)
        i += 1


def compile_solution(problem, compile_command):
    language = get_language()
    try:
        if language.ext in ('c', 'cpp', 'kt'):
            return subprocess.run([*compile_command.split(' '), f'{problem}.{language.ext}', '-o', problem], timeout=10)
        else:
            return subprocess.run([*compile_command.split(' '), f'{problem}.{language.ext}'], timeout=10)
    except subprocess.TimeoutExpired:
        print(error_style('Compilation time has exceeded 10 seconds.'))
        print('Make sure you are using appropriate compile and run commands for your language.')
        sys.exit()
    except OSError:
        print(error_style('Compile command is wrong or compiler is not installed.'))
        sys.exit()


def test_solution(problem, i, args):
    with open(os.path.join('in', f'{i}.in')) as input_file:
        test_in = input_file.read()
    with open(os.path.join('ans', f'{i}.out')) as answer_file:
        test_ans = answer_file.read()

    language = get_language()
    run_command = get_run_command()
    try:
        if run_command:
            if language.ext == 'java':
                r = subprocess.run([*run_command.split(' '), problem], input=test_in, capture_output=True,
                                   timeout=10, encoding='utf-8')
            else:
                r = subprocess.run([*run_command.split(' '), f'{problem}.{language.ext}'], input=test_in,
                                   capture_output=True, timeout=10, encoding='utf-8')
        else:
            r = subprocess.run('./' + problem, input=test_in, capture_output=True, timeout=10, encoding='utf-8')
        test_out = r.stdout.strip()
        test_err = r.stderr.strip()
    except FileNotFoundError:
        print(error_style('Executable file has not been found.'))
        print('Make sure you are using appropriate compile and run commands for your language.')
        sys.exit()
    except subprocess.TimeoutExpired:
        print(negative_style('Execution time exceeded 10 seconds.'))
        return

    if all(check_line(o, ans, args) for o, ans in zip(test_out.split('\n'), test_ans.split('\n'))):
        print(positive_style('Test passed'))
    else:
        print(negative_style('Test did not pass\n'))
        if test_err:
            print('Program error:', test_err, '', sep='\n')
        terminal_width = (shutil.get_terminal_size().columns - 4) // 2
        max_line_width = max(len(line) for line in test_out.split('\n') + test_ans.split('\n'))
        if max_line_width > terminal_width:
            print('Program output:', test_out, '', sep='\n')
            print('Answer:', test_ans, sep='\n')
        else:
            max_line_width = min(max(max_line_width + 4, 16), terminal_width)
            print(f'{"Program output:":{max_line_width}}    {"Answer:":{max_line_width}}')
            for out_line, ans_line in zip(test_out.split('\n'), test_ans.split('\n')):
                separator = negative_style(' ?  ') if not check_line(out_line, ans_line, args) else ' '*4
                print(f'{out_line:{max_line_width}}{separator}{ans_line:{max_line_width}}')
        print('')


def check_line(out_line, ans_line, args):
    if not args.precision:
        return out_line.split() == ans_line.split()
    else:
        for a, b in zip(out_line.split(), ans_line.split()):
            try:
                a, b = float(a), float(b)
            except ValueError:
                print(error_style('Some part of answer or output is not a floating point number.'))
                sys.exit()
            try:
                precision = float(args.precision)
            except ValueError:
                print(error_style('Precision should be a floating point number.'))
                sys.exit()

            cf_precision_check = abs(a - b) / max(1.0, abs(b)) <= precision    # relative or absolute error
            if not cf_precision_check:
                return False
    return True
