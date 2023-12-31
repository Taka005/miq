import sys
import textwrap
import unicodedata
from itertools import groupby

east_asian_widths = {
    'W': 2,   # Wide
    'F': 2,   # Full-width (wide)
    'Na': 1,  # Narrow
    'H': 1,   # Half-width (narrow)
    'N': 1,   # Neutral (not East Asian, treated as narrow)
    'A': 1    # Ambiguous (s/b wide in East Asian context, narrow otherwise, but that doesn't work)
}

def column_width(text):
    if isinstance(text, str) and sys.version_info < (3,0):
        return len(text)
    combining_correction = sum([-1 for c in text if unicodedata.combining(c)])
    try:
        width = sum([east_asian_widths[unicodedata.east_asian_width(c)] for c in text])
    except AttributeError:
        width = len(text)
    return width + combining_correction

class TextWrapper(textwrap.TextWrapper):
    def _wrap_chunks(self, chunks):
        lines = []

        chunks.reverse()

        while chunks:
            cur_line = []
            cur_len = 0

            if lines:
                indent = self.subsequent_indent
            else:
                indent = self.initial_indent

            width = self.width - column_width(indent)

            if self.drop_whitespace and chunks[-1].strip() == '' and lines:
                del chunks[-1]

            while chunks:
                l = column_width(chunks[-1])

                if cur_len + l <= width:
                    cur_line.append(chunks.pop())
                    cur_len += l

                else:
                    break

            if chunks and column_width(chunks[-1]) > width:
                self._handle_long_word(chunks, cur_line, cur_len, width)

            if self.drop_whitespace and cur_line and cur_line[-1].strip() == '':
                del cur_line[-1]

            if cur_line:
                lines.append(indent + ''.join(cur_line))

        return lines

    def _break_word(self, word, space_left):
        total = 0
        for i,c in enumerate(word):
            total += column_width(c)
            if total > space_left:
                return word[:i-1], word[i-1:]
        return word, ''

    def _split(self, text):
        split = lambda t: textwrap.TextWrapper._split(self, t)
        chunks = []
        for chunk in split(text):
            for w, g in groupby(chunk, column_width):
                if w == 1:
                    chunks.extend(split(''.join(g)))
                else:
                    chunks.extend(list(g))
        return chunks

    def _handle_long_word(self, reversed_chunks, cur_line, cur_len, width):
        space_left = max(width - cur_len, 1)
        if self.break_long_words:
            l, r = self._break_word(reversed_chunks[-1], space_left)
            cur_line.append(l)
            reversed_chunks[-1] = r

        elif not cur_line:
            cur_line.append(reversed_chunks.pop())

def fw_wrap(text,width=50):
    w = TextWrapper(width=width)
    return w.wrap(text)