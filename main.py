import random

generation = 1
POPULATION_SIZE = 2
GENES = '01'
TARGET = "01011101"
zap = [0]*32
uap = [5]*8
gap = [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
fap = [0]*32
kapap = 0
x = "00000000"

class Individual(object):
    def __init__(self, chromosome):
        self.chromosome = chromosome
        self.fitness = self.cal_fitness()

    @classmethod
    def mutated_genes(self):
        global GENES
        gene = random.choice(GENES)
        return gene

    @classmethod
    def create_gnome(self):
        global TARGET
        gnome_len = len(TARGET)
        return [self.mutated_genes() for _ in range(gnome_len)]

    def mate(self, par2):
        child_chromosome = []
        for gp1, gp2 in zip(self.chromosome, par2.chromosome):
            prob = random.random()
            if prob < 0.33:
                child_chromosome.append(gp1)

            elif prob < 0.66:
                child_chromosome.append(gp2)

            else:
                child_chromosome.append(self.mutated_genes())

        return Individual(child_chromosome)

    def cal_fitness(self):
        global TARGET
        global generation
        global x
        global zap
        global uap
        global gap
        global fitness
        fitness = 0
        dz = 0
        dx = 0
        i = 1
        gan = 0
        for gs, gt, gx in zip(self.chromosome, TARGET, x):
            dz = dz + int(gs)*i
            dx = dx + int(gx)*i
            i = i*10
            if i == 1000000:
                dz = dz + 100000000
                dx = dx + 100000000

        dzo = dz
        dzod = 0
        while (dzo > 0):
            Reminder = dzo % 10
            dzod = (dzod * 10) + Reminder
            dzo = dzo // 10
        dzodd = int(dzod/10) + 100000000
        gaud = int(dzodd/100000)
        gaur = int(dzodd%100000)
        jok = 1
        dafwo = 0
        for i in range(0,3):
            dfdo = gaud % 10
            gaud = int(gaud/10)
            dafwo += dfdo * jok
            jok = jok * 2
        if uap[dafwo] == 0:
            fitness += 2
        dafqo = 0
        joke = 1
        for i in range(0, 5):
            dfd = gaur % 10
            gaur = int(gaur / 10)
            dafqo += dfd * joke
            joke = joke * 2
        if gap[dafqo] == 0:
            fitness += 1
        if int(dz) == int(dx):
            generation -= 1
            fitness += 4
        if int(dzodd/100000) == 1111: fitness += 6
        if dzod%100000 == 11110 or dzod%100000 == 11111: fitness += 6
        if zap[29] == 0:
            fitness += 1
        else:
            fitness = 0
        return fitness

def main():
    global POPULATION_SIZE, dafq
    global x
    global generation
    global zap
    global gap
    global uap
    global fap
    global kapap

    if generation == 1: generation = 1

    found = False
    population = []

    for _ in range(POPULATION_SIZE):
        gnome = Individual.create_gnome()
        population.append(Individual(gnome))

    while not found:
        population = sorted(population, key=lambda x: x.fitness)
        if population[0].fitness <= 0:
            found = True
            break

        new_generation = []

        s = int((10 * POPULATION_SIZE) / 100)
        new_generation.extend(population[:s])

        s = int((90 * POPULATION_SIZE) / 100)
        for _ in range(s):
            parent1 = random.choice(population[:50])
            parent2 = random.choice(population[:50])
            child = parent1.mate(parent2)
            new_generation.append(child)

        population = new_generation

        x = population[0].chromosome
        z = 100000000
        for ij in range(0,8):
            lam = 10**(7-ij)
            z += int(x[ij])*lam

        flag = 0
        fak = z
        majq = int(fak/100000)
        majw = int(fak%100000)
        jok = 1
        dafw = 0
        for iz in range(0,3):
            dfdo = majq % 10
            majq = int(majq/10)
            dafw += dfdo * jok
            jok = jok * 2
        uap[dafw] = uap[dafw] - 1
        if uap[dafw] == -1:
            flag = 1
            uap[dafw] += 1
        elif dafw == 7:
            flag = 1
            uap[dafw] += 1
        else:
            dafq = 0
            joke = 1
            for idom in range(0, 5):
                dfd = majw % 10
                majw = int(majw / 10)
                dafq += dfd * joke
                joke = joke * 2
            gap[dafq] = gap[dafq] - 1
            if gap[dafq] == -1:
                flag = 1
                gap[dafq] += 1
                uap[dafw] += 1
            elif dafq == 31:
                flag = 1
                uap[dafw] += 1
            elif dafq == 30:
                flag = 1
                uap[dafw] += 1

        hau = generation
        if generation > 24:
            hau = 25
        for hh in range(0,hau):
            if z == zap[hh]:flag = 1
        if flag == 0:
            zap[kapap] = z
            kapap += 1

#        print("Generation: {}\tString: {}\tFitness: {}". \
#              format(generation,
#                     "".join(population[0].chromosome),
#                     population[0].fitness))

        generation += 1

        fd = population[0].fitness

        #if generation == 1:
        #    print("Generation: {}\tString: {}\tFitness: {}". \
        #        format(generation,
        #                 "".join(population[0].chromosome),
        #                 population[0].fitness))

    if fd == 0:
        print(zap)
        for i in range(0,30):
            dd = zap[i]
            majw = 0
            majw = int(dd)%100000
            dafq = 0
            joke = 1
            for idom in range(0, 5):
                dfd = majw % 10
                majw = int(majw / 10)
                dafq += dfd * joke
                joke = joke * 2
            majq = int(dd / 100000)
            jok = 1
            dafw = 0
            for iz in range(0, 3):
                dfdo = majq % 10
                majq = int(majq / 10)
                dafw += dfdo * jok
                jok = jok * 2
            fap[dafq] = dafw
#        print(fap)
        for i in range(0,5):
            if i == 0:
                print(" Mon ",end=" ")
            elif i == 1:
                print("\n Tue ",end=" ")
            elif i == 2:
                print("\n Wed ",end=" ")
            elif i == 3:
                print("\n Thu ",end=" ")
            elif i == 4:
                print("\n Fri ",end=" ")
            for j in range(0,6):
                zad = 0
                zad = fap[i*6+j] + 1
                if j  == 3:
                    print("// R //",end=" ")
                print(zad,end=" ")


if __name__ == '__main__':
    main()
