from tools import logging
import numpy as np
import csv
import gb_accelerate
import os

class Vocab():

    def __init__(self, origin_data_tokens, word_dim:int=100, vocab_limit_size=80000,
                 is_using_pretrained=True, word_vec_file_path=r'./static/glove.6B.100d.txt'):
        self.file_path = word_vec_file_path
        self.word_dim = word_dim
        self.word_dict = {}
        self.word_count = {}
        self.vectors = None
        self.num = 0
        self.data_tokens = []
        self.words_vocab = []
        assert len(origin_data_tokens) > 0
        self.data_tokens = origin_data_tokens
        self.__build_words_index()
        self.__limit_dict_size(vocab_limit_size)
        if is_using_pretrained:
            logging(f'building word vectors from {self.file_path}')
            self.__read_pretrained_word_vecs()
        logging(f'word vectors has been built! dict size is {self.num}')


    def __build_words_index(self):
        for sen in self.data_tokens:
            for word in sen:
                if word not in self.word_dict:
                    self.word_dict[word] = self.num
                    self.word_count[word] = 1
                    self.num += 1
                else:
                    self.word_count[word] += 1


    def __limit_dict_size(self, vocab_limit_size):
        limit = vocab_limit_size
        self.word_count = sorted(self.word_count.items(), key=lambda x: x[1], reverse=True)
        count = 1
        self.words_vocab.append('<unk>')
        temp = {}
        for x, y in self.word_count:
            if count > limit:
                break
            temp[x] = count
            self.words_vocab.append(x)
            count += 1
        self.word_dict = temp
        self.word_dict['<unk>'] = 0
        self.num = count
        assert self.num == len(self.word_dict) == len(self.words_vocab)
        self.vectors = np.ndarray([self.num, self.word_dim], dtype='float32')

    def __read_pretrained_word_vecs(self):
        num = 0
        word_dict = {}
        word_dict['<unk>'] = 0  # unknown word
        with open(self.file_path, 'r', encoding='utf-8') as file:
            file = file.readlines()
            vectors = np.ndarray([len(file) + 1, self.word_dim], dtype='float32')
            vectors[0] = np.random.normal(0.0, 0.3, [self.word_dim]) #unk
            for line in file:
                line = line.split()
                num += 1
                word_dict[line[0]] = num
                vectors[num] = np.asarray(line[-self.word_dim:], dtype='float32')


        for word, idx in self.word_dict.items():
            if idx == 0: continue
            if word in word_dict:
                key = word_dict[word]
                self.vectors[idx] = vectors[key]
            else: self.vectors[idx] = vectors[0]
        self.init_vector = vectors[0]


    def __len__(self):
        return self.num

    def get_index(self, word: str):
        if self.word_dict.get(word) is None:
            return 0  # unknown word
        return self.word_dict[word]

    def get_word(self, index:int):
        return self.words_vocab[index]

    def get_vec(self, index: int):
        assert self.vectors is not None
        return self.vectors[index]

    def read_syn_csv(self, path):
        logging(f"reading syn in {path}")
        with open(path, 'r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file, delimiter=',')
            label = 0
            data = []
            for line in reader:
                for word in line:
                    idx = self.get_index(word)
                    if idx:
                      temp = [label] + list(self.get_vec(idx))
                      data.append(temp)
                label += 1
            logging(f"have {label}, data shape {len(data)}, {len(data[0])}")
            return data
     
    def create_syn_vocab_latest(self, path, purity, vec_path):
        if os.path.exists(vec_path):
            self.vectors = np.load(vec_path)
            logging(f"load syn_vocab success! from {vec_path}")
        else:
            data = self.read_syn_csv(path)
            numbers, result, centers, _ = gb_accelerate.main(np.array(data), purity)
            for id, number in enumerate(numbers):
                for i in result[id]:
                    index = np.where((self.vectors == i[1:]).all(axis=1))
                    self.vectors[index, :] = centers[id][1:]
            np.save(vec_path, self.vectors)
            logging(f"create syn_vocab success! has {len(numbers)} balls")
      
if __name__ == '__main__':
    pass
