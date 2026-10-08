import java.util.*;
import java.util.stream.*;


    record Student(long rollNum, String name, int age, float marks){
    }

    public class Sample{

        public static <T> void print(T t){
            System.out.println(t);
        }

        public static void main(String... args){
            List<Integer> list = Arrays.asList(0,1,2,3,4,5,6,7,8,9,21,43,45,76,78);
            List<String> str = Arrays.asList("pavan", "kalyan","Aruna","Bhaskar","java");
            List<Student> students = Arrays.asList(
                new Student(1001,"Pavan", 21,99.87f),
                new Student(1002,"kalyan", 21,100f),
                new Student(1003,"bhaskar", 21,94.87f),
                new Student(1004,"aruna", 21,79.87f),
                new Student(1005,"Java babu", 31,39.87f),
                new Student(1006,"Pythoni", 43,69.87f),
                new Student(1007,"Scala rao", 43,49.87f)
            );
        Sample s = new Sample();
        s.countVowels("Hey there, I'm Pavan Kalyan");

    }

    // Easy Problems

    public void sum(List<Integer> list){
        list.stream().mapToInt(Integer::intValue).sum();
        list.stream().mapToInt(i -> i.intValue()).sum();
        list.stream().reduce(0,Integer::sum);
    }

    public void product(List<Integer> list){
        list.stream().reduce(1, (a,b) -> a*b);
        Optional<Integer> product = list.stream().reduce((a,b) -> a*b);
        print(product);
        list.stream().collect(Collectors.reducing(1, (a,b) -> a*b));
    }

    public void average(Set<Integer> set){
        set.stream().mapToInt(Integer::intValue).average().orElse(0);
    }

    public void max(List<Integer> list){
        list.stream().mapToInt(Integer::intValue).max();
        list.stream().max(Integer::compare).orElse(0);
        list.stream().max(Integer::compareTo).orElse(0);
        list.stream().sorted(Comparator.reverseOrder()).findFirst().orElse(0);
        list.stream().sorted().reduce((i,j) -> j).orElse(0);
        // without using min(), max(), sorted...
        list.stream().reduce((a,b) -> a > b ? a : b);

    }

    public void min(List<Integer> list){
        list.stream().min(Integer::compareTo).orElse(0);
        list.stream().min(Integer::compare).orElse(0);
        list.stream().mapToInt(Integer::intValue).min();
        list.stream().sorted().findFirst().orElse(0);
        list.stream().sorted().reduce((i,j) -> i).orElse(0);
        // without using min(), max(), sorted...
        list.stream().reduce((a,b) -> a < b ? a : b);
    }

    public void count(List<Integer> list){
        list.stream().count();
    }

    public void check(List<Integer> list, int key){
        list.stream().anyMatch(i -> i==key);
        print(list.stream().filter(i -> i==key).findFirst().isPresent());
        print(list.stream().anyMatch(i -> i==key));
    }

    public void evens(List<Integer> list){
        print(list.stream().filter(i -> i%2==0).map(String::valueOf).collect(Collectors.joining(",")));
        Map<Boolean, List<Integer>> checkers = list.stream().collect(Collectors.partitioningBy(i -> i%2==0));
        List<Integer> even = checkers.get(true);
        List<Integer> odd = checkers.get(false);
        print(even+"+"+odd);
    }

    public void upperCase(List<String> string){
        string.stream().map(String::toUpperCase).collect(Collectors.joining(":"));
        string.stream().map(String::toLowerCase).collect(Collectors.toList());
    }

    public void squares(List<Integer> list){
        list.stream().map(i->i*i).collect(Collectors.toList());
    }

    public void findFirstt(List<Integer> list){
        list.stream().findFirst().orElse(0);
    }

    public void findLast(List<Integer> list) {
        list.stream().reduce((i,j) -> j).orElse(0);
    }

    public void checkAll(List<Integer> list) {
        list.stream().allMatch(n -> n%2==0);
        list.stream().anyMatch(n-> n%2==0);
    }

    public void removeDups(List<Integer> list){
        Set<Integer> unq = list.stream().distinct().collect(Collectors.toSet());
    }

    public void sortt(List<Integer> list){
        list.stream().mapToInt(Integer::intValue).sorted();   // Cant sort a intStream in reverse order. Change it Integer Stream and then sort it in desc...
        list.stream().sorted().collect(Collectors.toList());
        list.stream().sorted(Comparator.reverseOrder()).collect(Collectors.toList());
    }

    public void sortStrings(List<String> str){
        str.stream().sorted().collect(Collectors.toList());

        str.stream().sorted(Comparator.comparingInt(i -> i.length())).collect(Collectors.toList());
        str.stream().sorted(Comparator.comparingInt(String::length)).collect(Collectors.joining("-"));
    }
    
    // Intermediate Problems

    public void findSumOfDigits(int n){
        String.valueOf(n).chars().map(Character::getNumericValue).sum();
    }

    public void factorial(int n) {
        LongStream.rangeClosed(1, n).reduce(1, (a,b) -> a*b);
    }

    public void secondLargest(List<Integer> list) {
        list.stream().sorted(Comparator.reverseOrder()).distinct().skip(1).findFirst().orElse(999);
    }

    public void secondSmallest(List<Integer> list) {
        list.stream().sorted().skip(1).findFirst().orElse(0);
    }

    public void longestString(List<String> str){
        print(str.stream().max(Comparator.comparing(String::length)).orElse(null)); // slower
        print(str.stream().min(Comparator.comparing(String::length)).orElse(null)); // slower
        str.stream().max(Comparator.comparingInt(String::length)).orElse(null); //faster
        str.stream().min(Comparator.comparingInt(String::length)).orElse(null); //faster
    }

    public void stringGrouping(List<String> str){
        Map<Integer, List<String>> map = str.stream().collect(Collectors.groupingBy(String::length));
    }


    public void compareMarks(List<Student> students) {
        Comparator<Student> comparator = (s1,s2) -> Float.compare(s1.marks(),s2.marks());
        students.sort(comparator.reversed());
        students.sort(Comparator.comparingDouble(Student::marks).reversed());
        print(students);
        students.stream().sorted(Comparator.comparingDouble(Student::marks).reversed()).forEach(System.out::println);
    }

    public void groupByAge(List<Student> students){
        Map<Integer, List<String>> map = students.stream()
        .collect(Collectors.groupingBy(
            Student::age, 
            Collectors.mapping(Student::name, Collectors.toList())
        ));

        Map<String, Long> results = students.stream()
        .collect(Collectors.groupingBy(s -> s.marks() > 40.0f ? "Pass" : "Fail",
                Collectors.counting()));
        print("Grouped By Age : " + map);
        print("Results : " + results);
    }

    public void partitionEven(List<Integer> list){
        Map<String,List<Integer>> partitions = list.stream().collect(Collectors.groupingBy(i -> i%2 == 0 ? "Even" : "Odd"));
        Map<Boolean, List<Integer>> partitionby = list.stream().collect(Collectors.partitioningBy(i -> i%2==0));
    }

    public void mergeList(List<Integer> list){
        List<Integer> merged = Stream.of(list, Arrays.asList(1,2,3,4)).flatMap(List::stream).collect(Collectors.toList());
        Stream.concat(list.stream(), List.of(1,2,3,4).stream()).collect(Collectors.toList());
    }

    public void intersection(List<Integer> list) {
        // intersection - common elements in both the lists..
        List<Integer> list2 = Arrays.asList(2,3,4,5,65,7,7);
        list.stream().filter(list2::contains).collect(Collectors.toList());
    }

    public void union(List<Integer> list){
        //common - uncommon everything
        List<Integer> list2 = Arrays.asList(1,2,3,4,5,6,7,8);
        Stream.of(list,list2).flatMap(List::stream).distinct().collect(Collectors.toList());
        Stream.concat(list.stream(), list2.stream()).distinct().collect(Collectors.toList());
    }

    public void difference(List<Integer> list){
        //unique elements from each list
        List<Integer> list2 = Arrays.asList(1,2,3,4,5,6,6,7);
        list.stream().filter(n -> !list2.contains(n)).collect(Collectors.toList()); //List1 - List2
        list2.stream().filter(i -> !list.contains(i)).collect(Collectors.toList()); //list2 - list1
    }

    public void counter(List<Integer> list){
        Map<Integer, Long> counter = list.stream().collect(Collectors.groupingBy(i->i,Collectors.counting()));
    }

    public void charCounter(String s){
        //chars() gives an IntStream. Why? cuz it returns ascii values of each character in a string and makes a stream of ints...
        s.chars().mapToObj(c -> (char) c).collect(Collectors.groupingBy(i->i, Collectors.counting()));
    }

    public void wordCounter(List<String> str){
        str.stream().collect(Collectors.groupingBy(i->i, Collectors.counting()));

        String s = "I gotta get into a project. Now or never. I gotta get into it no matter what...";
        Arrays.stream(s.split(" ")).collect(Collectors.groupingBy(i->i,Collectors.counting()));
    }

    public void countVowels(String s){
        List<Character> list = Arrays.asList('a','e','i','o','u');
        Map<Character,Long> countMapp = s.toLowerCase().chars().mapToObj(c-> (char) c).filter(c -> list.contains(c)).collect(Collectors.groupingBy(c->c, Collectors.counting()));
        Map<Character, Long> map = s.toLowerCase().chars().mapToObj(c -> (char) c).filter(i -> "aeiou".contains(String.valueOf(i))).collect(Collectors.groupingBy(x->x,
                         Collectors.counting()
                            ));
        
    }

    public void countDigits(String s){
        s.chars().mapToObj(c -> (char) c).filter(Character::isDigit).collect(Collectors.groupingBy(c->c, Collectors.counting()));
    }

    public void reverseList(List<Integer> list){
        list.stream().collect(Collectors.collectingAndThen(Collectors.toList(), 
            x -> {Collections.reverse(x);
                return x;
            }));
    }

    public void reverseString(String s){
        s.chars().mapToObj(c -> String.valueOf((char) c)).reduce("",(a,b)-> b+a);
    }


    // Advanced Problems
    public void sumCheck(List<Integer> list){
        Map<String, List<Integers>> = 
        list.stream().collect(Collectors.groupingBy( (a,b) -> a+b = 5 ? "Match" : "No Match", Collectors.toList()));
    }

}