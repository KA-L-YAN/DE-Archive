package practice;
import java.util.*;
import java.util.stream.Collector;
import java.util.stream.Collectors;

public class Streamz {

    public static List<Integer> list = new ArrayList<>(Arrays.asList(1,2,2,3,4,5,3,3,4,5,6,7));
    public static List<String> strings = Arrays.asList("pavan","kalyan","java","python","aws","data","eng");

    public static <T> void print(T t){
        System.out.println(t);
    }

    /**
     * 1. Find the Sum of All Elements in a List
     * 2. Find the Product of All Elements in a List
     * 3. Find the Average of All Elements in a List
     * 4. Find the Maximum Element in a List
     * 5. Find the Minimum Element in a List
     * 6. Count the Number of Elements in a List
     * 7. Check if a List Contains a Specific Element
     * 8. Filter Out Even Numbers from a List
     * 9. Filter Out Odd Numbers from a List
     * 10. Convert a List of Strings to UpperCase
     * 11. Convert a List of Integers to Their Squares
     * 12. Find the First Element in a List
     */
    
    public static void main(String... args){
        int oneSum = list.stream().mapToInt(Integer::intValue).sum();
        int oneSum2 = list.stream().reduce(0, (a,b) -> a+b);
        print(list.stream().reduce(0,Integer::sum)); // Directly using Integer.sum()
        print("oneSum : "+oneSum); print("oneSum2 : "+oneSum2);
        long twoProduct = list.stream().reduce(1, (a,b) -> a*b);
        print("twoProduct : " +twoProduct);
        print("average : "+ list.stream().mapToInt(Integer::intValue).average().orElse(0));
        print("Max : "+list.stream().mapToInt(Integer::intValue).max());
        print("Max : "+list.stream().max(Integer::compare).orElse(0));
        print("Min : "+list.stream().mapToInt(Integer::intValue).min());
        print("Min : "+list.stream().min(Integer::compare).orElse(0));
        print("count : "+list.stream().count());
        print("7. Is the element 3 in the list? : "+list.stream().anyMatch(i -> i==3));
        list.stream().filter(i->i==3).forEach(System.out::println);
        print("Even Nums : "+list.stream().filter(i->i%2==0).collect(Collectors.toList()));
        print("Odd : "+list.stream().filter(i->i%2!=0).collect(Collectors.toSet()));
        print("To Uppercase : "+strings.stream().map(String::toUpperCase).collect(Collectors.toList()));
        print("Square Roots : "+list.stream().map(Math::sqrt).collect(Collectors.toList()));
        print("Squares : "+list.stream().map(i->i*i).collect(Collectors.toList()));
        print("First element : "+list.stream().findFirst().orElse(null));

        Set<Integer> hSet = list.stream().distinct().collect((Collectors.toSet()));
        print("After dups removal : " + hSet);

        Map<Integer, Long> mapp = list.stream().collect(Collectors.groupingBy(Integer::intValue,Collectors.counting()));
        print(mapp);


        ListIterator<Integer> listIter = list.listIterator();
        while(listIter.hasNext()){
            if(listIter.next() == 3){
                listIter.remove();
            }
        } 
        print(list);

        Set<Integer> dups = new LinkedHashSet<>();
        
        List<Integer> lDups = list.stream().filter(i -> !dups.add(i)).distinct().collect(Collectors.toList());
        print("Dups : " +lDups);
        print(dups);


    }
}